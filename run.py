import os
import json
import base64
import subprocess
import requests
import wave
import contextlib
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from faster_whisper import WhisperModel

load_dotenv("backend/.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

ROOT_DIR = Path(__file__).parent.resolve()
PUBLIC_DIR = ROOT_DIR / "video-engine" / "public"
OUT_DIR = ROOT_DIR / "exports"
OUT_DIR.mkdir(exist_ok=True)

client = genai.Client(api_key=GEMINI_API_KEY)
whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")

# Language to Sarvam Speaker Mapping
LANGUAGE_MAP = {
    "Telugu": {"code": "te-IN", "speaker": "kavya"},   # Beautiful, fluent South Indian female voice
    "Hindi": {"code": "hi-IN", "speaker": "priya"},    # Clear, pleasant Hindi female voice
    "Tamil": {"code": "ta-IN", "speaker": "kavitha"},  # Native-sounding Tamil female voice
    "English": {"code": "en-IN", "speaker": "shruti"}  # Professional Indian-accent female voice
}

def generate_script(listing: dict) -> dict:
    language = listing.get("language", "Telugu")
    custom_instructions = listing.get("custom_instructions", "")
    
    # If the user asked for specific changes, inject them heavily into the prompt
    instruction_block = f"\nCRITICAL USER INSTRUCTIONS (APPLY STRICTLY): {custom_instructions}\n" if custom_instructions else ""

    print(f"\n[1/7] Generating {language} script for {listing.get('category')}...")
    prompt = f"""
    Create a fast-paced, high-energy Instagram Reel script for selling this:
    Category: {listing.get('category')}
    Title: {listing.get('title')}
    Specs: {listing.get('specs')}
    Price: {listing.get('price')}

    LANGUAGE TARGET: {language}
    {instruction_block}
    
    CRITICAL CONSTRAINTS & FLUENCY:
    1. STRICT CHARACTER LIMIT: The `spoken_script` MUST NOT EXCEED 400 CHARACTERS.
    2. Use frequent commas (,) and periods (.) to force natural pauses. 
    3. Spell out all numbers phonetically (e.g., "forty five thousand").

    Output pure JSON matching:
    {{
        "hook_text": "3-5 word capitalized punchy headline in English",
        "spoken_script": "The highly punctuated script (STRICTLY UNDER 400 CHARACTERS).",
        "b_roll_keyword": "1-2 word precise search keyword"
    }}
    """
    
    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash"]
    for model_name in candidate_models:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            meta = json.loads(res.text)
            
            # Python Failsafe: Hard truncate to prevent Sarvam API crash
            script = meta.get("spoken_script", "")
            if len(script) > 495:
                meta["spoken_script"] = script[:495]
                
            return meta
        except Exception:
            continue
    raise RuntimeError("Failed to generate script.")


def generate_audio(text: str, language: str, filename="output_audio.wav"):
    print(f"[2/6] Generating voiceover via Sarvam AI ({language})...")
    url = "https://api.sarvam.ai/text-to-speech"
    clean_text = text.replace("*", "").replace("#", "").strip()
    
    lang_settings = LANGUAGE_MAP.get(language, LANGUAGE_MAP["Telugu"])

    payload = {
        "inputs": [clean_text],
        "target_language_code": lang_settings["code"],
        "speaker": lang_settings["speaker"],
        "model": "bulbul:v3",
        "enable_preprocessing": True
    }
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }

    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 200:
        audio_data = base64.b64decode(res.json()["audios"][0])
        target_path = PUBLIC_DIR / filename
        with open(target_path, "wb") as f:
            f.write(audio_data)
        
        # Calculate Audio Duration precisely
        with contextlib.closing(wave.open(str(target_path), 'r')) as w:
            frames = w.getnframes()
            rate = w.getframerate()
            duration = frames / float(rate)
            
        print(f"-> Audio ready: {duration:.1f} seconds")
        return filename, duration
    raise Exception(f"Sarvam AI failed: {res.text}")


def extract_word_timestamps(audio_path: str):
    print("[3/6] Generating word-level subtitle sync via Whisper...")
    segments, _ = whisper_model.transcribe(audio_path, word_timestamps=True)
    word_timings = []
    for segment in segments:
        if segment.words:
            for word in segment.words:
                cleaned = word.word.strip()
                if cleaned:
                    word_timings.append({"word": cleaned, "start": round(word.start, 2), "end": round(word.end, 2)})
    return word_timings


import yt_dlp

def fetch_youtube_trailer(vehicle_name: str, filename: str = "broll.mp4"):
    print(f"[4/6] Searching YouTube for official trailer: '{vehicle_name}'...")
    target_path = PUBLIC_DIR / filename
    
    # We search for a vertical short or cinematic trailer
    search_query = f"ytsearch1:{vehicle_name} official cinematic trailer shorts"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/mp4',
        'outtmpl': str(target_path),
        'noplaylist': True,
        'quiet': True,
        'max_filesize': 50 * 1024 * 1024, # Max 50MB to keep it fast
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([search_query])
        print(f"-> Downloaded exact model trailer!")
        return filename
    except Exception as e:
        print(f"-> YouTube fetch failed: {e}. Falling back to default...")
        return None


def render_video(props: dict, output_filename: str):
    print("[5/6] Passing dynamic props to Remotion...")
    props_json_path = ROOT_DIR / "temp_props.json"
    with open(props_json_path, "w", encoding="utf-8") as f:
        json.dump(props, f)

    output_path = OUT_DIR / output_filename
    print(f"[6/6] Rendering video to {output_path}...")
    cmd = [
        "npx.cmd" if os.name == "nt" else "npx",
        "remotion", "render", "AutoReel", str(output_path),
        f"--props={str(props_json_path)}"
    ]
    subprocess.run(cmd, cwd=str(ROOT_DIR / "video-engine"), check=True)
    if props_json_path.exists(): props_json_path.unlink()
    print(f"\n[DONE] Reel saved to: {output_path}")
    
    
def extract_details_from_user(text: str, audio_path: str = None) -> dict:
    print("[*] AI is extracting listing details from user message/voice note...")
    
    prompt = """
    You are an AI assistant for an automated video reel generator. 
    Extract the vehicle/property details and any custom user instructions from the provided text or audio.
    
    Output pure JSON matching this exact structure:
    {
        "category": "e.g., Sports Bike, SUV, Luxury Villa (guess if not explicit)",
        "title": "e.g., Yamaha R15 V3",
        "specs": "e.g., 18,000 KM • Single Owner (summarize key points)",
        "price": "e.g., 1.45 Lakhs",
        "language": "Telugu, Hindi, or English (default to Telugu if not specified)",
        "custom_instructions": "Any specific requests for BGM, vibe, templates, or script changes"
    }
    """
    
    contents = [prompt]
    
    if audio_path and os.path.exists(audio_path):
        sample_audio = client.files.upload(file=audio_path)
        contents.append(sample_audio)
    
    if text:
        contents.append(f"User Text Message: {text}")

    candidate_models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-3.5-flash-lite"]
    for model_name in candidate_models:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(res.text)
        except Exception as e:
            continue
            
    raise RuntimeError("Failed to parse user input.")