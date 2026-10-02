import os
import json
import base64
import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_tenglish_script(listing: dict) -> dict:
    """
    Generates a viral Tenglish hook, TTS script, and b-roll keyword.
    """
    category = listing.get("category", "property/vehicle")
    print(f"1. Generating Tenglish script for {category.upper()}...")

    prompt = f"""
    You are an expert Instagram Reel scriptwriter for Indian local sales content.
    A user wants to sell this {category}:
    - Title / Item: {listing.get('title')}
    - Key Specs: {listing.get('specs')}
    - Location: {listing.get('location', 'Prime Location')}
    - Price: {listing.get('price')}
    - Highlights: {listing.get('highlights')}

    Generate a JSON response:
    1. "hook_text": A 3-5 word attention-grabbing headline (e.g. 'DREAM VILLA FOR SALE', 'LOW KM BIKE DEAL').
    2. "spoken_script": A 30-second conversational Tenglish (Telugu + English) script.
       - Energetic local influencer style.
       - Spell out prices, square feet, yards, or km in full spoken words for natural TTS pronunciation (e.g., 'fifty five lakhs only', 'two hundred square yards').
    3. "b_roll_keyword": A 1-2 word search keyword for portrait stock footage (e.g. 'modern house', 'motorcycle ride', 'car highway').

    Respond ONLY in valid JSON matching this schema:
    {{
        "hook_text": "string",
        "spoken_script": "string",
        "b_roll_keyword": "string"
    }}
    """

    candidate_models = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
    ]
    for model_name in candidate_models:
        try:
            print(f"-> Generating with {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            if response.text:
                return json.loads(response.text)
        except Exception as e:
            print(f"   [Notice] {model_name} failed: {e}. Trying next...")

    raise RuntimeError("Could not generate script with available models.")


def synthesize_sarvam_audio(text: str, output_path: str = "output_audio.wav"):
    """
    Converts Tenglish script into native speech using Sarvam AI Bulbul v3.
    """
    print("2. Generating native audio via Sarvam AI...")
    url = "https://api.sarvam.ai/text-to-speech"

    payload = {
        "inputs": [text],
        "target_language_code": "te-IN",
        "speaker": "shubh",
        "model": "bulbul:v3",
        "enable_preprocessing": True,
    }

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json",
    }

    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 200:
        audio_base64 = res.json()["audios"][0]
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(audio_base64))
        print(f"-> Audio saved: {output_path}")
        return output_path
    else:
        raise Exception(f"Sarvam AI Error ({res.status_code}): {res.text}")


def fetch_pexels_broll(query: str, output_path: str = "broll.mp4"):
    """
    Fetches a vertical (9:16) stock video clip from Pexels API.
    """
    print(f"3. Searching Pexels for vertical B-Roll: '{query}'...")
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=1"
    headers = {"Authorization": PEXELS_API_KEY}

    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        if data.get("videos"):
            video_files = data["videos"][0]["video_files"]
            hd_file = next(
                (f for f in video_files if f.get("width") == 1080),
                video_files[0],
            )
            video_url = hd_file["link"]

            v_res = requests.get(video_url)
            with open(output_path, "wb") as f:
                f.write(v_res.content)
            print(f"-> B-roll video saved: {output_path}")
            return output_path
    print("-> No vertical B-roll found, continuing without stock clip.")
    return None


if __name__ == "__main__":
    sample_item = {
        "category": "Car",
        "title": "Hyundai Creta SX 2021",
        "specs": "45,000 km • Petrol • Manual",
        "location": "Hyderabad",
        "price": "11.75 Lakhs",
        "highlights": "Single owner, panoramic sunroof, mint condition",
    }

    # 1. Script
    script_data = generate_tenglish_script(sample_item)
    print("\n--- Generated Metadata ---")
    print(json.dumps(script_data, indent=2, ensure_ascii=False))

    # 2. Audio
    synthesize_sarvam_audio(script_data["spoken_script"])

    # 3. B-Roll
    fetch_pexels_broll(script_data["b_roll_keyword"])

    print("\n[Phase 1 Assets Ready!]")