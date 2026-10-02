import requests 
import os
import io
import json
import uuid
import shutil
import urllib.request
from fastapi import BackgroundTasks, Request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your_sid_here")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_token_here")
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"  # Default Twilio sandbox number

# Initialize Twilio Client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from rembg import remove
from PIL import Image

from run import (
    generate_script, generate_audio, extract_word_timestamps, 
    fetch_youtube_trailer, render_video, PUBLIC_DIR, OUT_DIR
)

app = FastAPI(title="Auto Reel Studio")
app.mount("/exports", StaticFiles(directory=str(OUT_DIR)), name="exports")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Auto Reel Studio - PRO</title>
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-white min-h-screen flex justify-center items-center py-10 font-sans">
      <div class="max-w-xl w-full bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl space-y-6">
        <h1 class="text-3xl font-black">⚡ Auto Reel Studio PRO</h1>
        <form id="reelForm" class="space-y-4">
          
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">Language</label>
            <select name="language" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 outline-none">
                <option value="Telugu">Telugu (Tenglish)</option>
                <option value="Hindi">Hindi (Hinglish)</option>
                <option value="English">English (Indian Accent)</option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-400 mb-1">Category (e.g. Sports Bike)</label>
              <input type="text" name="category" value="Sports Bike" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5">
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-400 mb-1">Price</label>
              <input type="text" name="price" value="₹1.45 Lakhs" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5">
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">Vehicle/Property Model</label>
            <input type="text" name="title" value="Yamaha R15 V3" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5">
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">Specs & Details</label>
            <input type="text" name="specs" value="18,000 KM • Single Owner" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5">
          </div>
          
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-400 mb-1">Watermark (Insta Handle)</label>
              <input type="text" name="watermark" value="@VizagMotors" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5">
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-400 mb-1">Urgency Tag</label>
              <input type="text" name="urgency" value="ONLY 1 LEFT!" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5">
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-amber-400 mb-1">Images (Backgrounds will be auto-removed)</label>
            <input type="file" name="images" multiple accept="image/*" required class="w-full bg-slate-800 rounded-xl py-2 file:bg-indigo-600 file:border-0 file:px-4 file:py-1 file:rounded file:text-white cursor-pointer">
          </div>

          <button type="submit" id="submitBtn" class="w-full py-3 bg-indigo-600 hover:bg-indigo-500 font-bold rounded-xl shadow-lg mt-2">Generate AI Reel</button>
        </form>

        <div id="statusBox" class="hidden text-indigo-400 text-center text-sm font-medium animate-pulse">Running pipeline (AI Background Removal takes a moment)...</div>
        
        <div id="resultBox" class="hidden space-y-4">
          <video id="reelVideo" controls class="w-full aspect-[9/16] rounded-xl bg-black border border-slate-700"></video>
          <a id="downloadLink" href="#" download class="block text-center py-3 bg-emerald-600 rounded-xl font-bold">Download Reel</a>
        </div>
      </div>

      <script>
        const form = document.getElementById('reelForm');
        form.onsubmit = async (e) => {
          e.preventDefault();
          document.getElementById('submitBtn').disabled = true;
          document.getElementById('statusBox').classList.remove('hidden');
          document.getElementById('resultBox').classList.add('hidden');
          
          try {
            const res = await fetch('/generate', { method: 'POST', body: new FormData(form) });
            const data = await res.json();
            if(!res.ok) throw new Error(data.detail);
            
            document.getElementById('reelVideo').src = data.video_url;
            document.getElementById('downloadLink').href = data.video_url;
            document.getElementById('resultBox').classList.remove('hidden');
            document.getElementById('statusBox').innerText = "Done!";
          } catch(err) {
            document.getElementById('statusBox').innerText = "Error: " + err.message;
          } finally {
            document.getElementById('submitBtn').disabled = false;
            document.getElementById('statusBox').classList.remove('animate-pulse');
          }
        };
      </script>
    </body>
    </html>
    """

@app.post("/generate")
async def generate_reel_endpoint(
    language: str = Form(...),
    category: str = Form(...),
    title: str = Form(...),
    specs: str = Form(...),
    price: str = Form(...),
    watermark: str = Form(...),
    urgency: str = Form(...),
    images: List[UploadFile] = File(...)
):
    session_id = uuid.uuid4().hex[:6]
    saved_images = []

    print("[1/7] Removing backgrounds using AI...")
    for idx, upload in enumerate(images):
        img_bytes = await upload.read()
        try:
            # Remove background using rembg
            result_bytes = remove(img_bytes)
            img = Image.open(io.BytesIO(result_bytes))
            img_name = f"up_{session_id}_{idx}.png" # Must be PNG for transparency
            img.save(PUBLIC_DIR / img_name, format="PNG")
            saved_images.append(img_name)
        except Exception as e:
            print(f"Background removal failed for image {idx}: {e}")
            raise HTTPException(status_code=500, detail="Image processing failed.")

    listing_data = {"category": category, "title": title, "specs": specs, "price": price, "location": "India"}

    try:
        meta = generate_script(listing_data, language)
        
        audio_name = f"audio_{session_id}.wav"
        _, duration_seconds = generate_audio(meta["spoken_script"], language, audio_name)
        duration_frames = int(duration_seconds * 30) + 15 

        word_captions = extract_word_timestamps(str(PUBLIC_DIR / audio_name))
        
        # NOTE: Keeping fetch_youtube_trailer here from your idea!
        broll_name = fetch_youtube_trailer(title, f"broll_{session_id}.mp4")

        output_filename = f"reel_{session_id}.mp4"
        remotion_props = {
            "hookText": meta["hook_text"],
            "priceText": price,
            "specsText": specs,
            "images": saved_images,
            "audioFileName": audio_name,
            "bgmFileName": "bgm.mp3",
            "subtitles": word_captions,
            "durationInFrames": duration_frames,
            "brollFileName": broll_name,
            "watermarkText": watermark,
            "urgencyText": urgency
        }

        render_video(remotion_props, output_filename)
        return {"status": "success", "video_url": f"/exports/{output_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
      
      

def background_whatsapp_pipeline(sender_number: str, session_id: str, text_body: str, image_urls: list, audio_url: str = None):
    try:
        # 1. Handle Voice Note Download if present
        audio_path = None
        if audio_url:
            audio_path = str(PUBLIC_DIR / f"voicenote_{session_id}.ogg")
            # Twilio media URLs can be downloaded directly
            r = requests.get(audio_url)
            with open(audio_path, 'wb') as f:
                f.write(r.content)

        # 2. Let Gemini figure out all the details dynamically!
        listing_data = extract_details_from_user(text_body, audio_path)
        
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=sender_number,
            body=f"🧠 Got it! Building a {listing_data['language']} reel for the {listing_data['title']}..."
        )

        # 3. Process Images (Virtual Showroom)
        saved_images = []
        for idx, url in enumerate(image_urls):
            img_name = f"up_{session_id}_{idx}.png"
            target_path = PUBLIC_DIR / img_name
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            img_bytes = urllib.request.urlopen(req).read()
            
            result_bytes = remove(img_bytes) # Background removal
            img = Image.open(io.BytesIO(result_bytes))
            img.save(target_path, format="PNG")
            saved_images.append(img_name)

        # 4. Run the Pipeline
        meta = generate_script(listing_data)
        audio_name = f"audio_{session_id}.wav"
        _, duration_seconds = generate_audio(meta["spoken_script"], listing_data['language'], audio_name)
        duration_frames = int(duration_seconds * 30) + 15 
        
        word_captions = extract_word_timestamps(str(PUBLIC_DIR / audio_name))
        broll_name = fetch_youtube_trailer(listing_data['title'], f"broll_{session_id}.mp4")

        output_filename = f"reel_{session_id}.mp4"
        remotion_props = {
            "hookText": meta["hook_text"],
            "priceText": listing_data["price"],
            "specsText": listing_data["specs"],
            "images": saved_images,
            "audioFileName": audio_name,
            "subtitles": word_captions,
            "durationInFrames": duration_frames,
            "brollFileName": broll_name,
            "watermarkText": "@YourAutoBot",
            "urgencyText": "DM TO BUY!"
        }

        render_video(remotion_props, output_filename)

        # 5. Send Video Back
        public_video_url = f"https://your-ngrok-url.app/exports/{output_filename}"
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=sender_number,
            body="✅ Your custom AI Reel is ready!",
            media_url=[public_video_url]
        )

    except Exception as e:
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=sender_number,
            body=f"⚠️ Pipeline Error: {str(e)}"
        )


@app.post("/whatsapp-webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    
    sender_number = form_data.get("From")
    text_body = form_data.get("Body", "").strip()
    num_media = int(form_data.get("NumMedia", 0))
    
    image_urls = []
    audio_url = None
    
    # Sort incoming media into images vs audio (Voice Notes)
    for i in range(num_media):
        content_type = form_data.get(f"MediaContentType{i}", "")
        media_url = form_data.get(f"MediaUrl{i}")
        
        if "audio" in content_type:
            audio_url = media_url
        elif "image" in content_type:
            image_urls.append(media_url)

    # Validate
    if len(image_urls) < 2:
        resp = MessagingResponse()
        resp.message("❌ Please attach at least 2 photos of the vehicle/property!")
        return HTMLResponse(content=str(resp), media_type="application/xml")

    if not text_body and not audio_url:
        resp = MessagingResponse()
        resp.message("❌ Please provide details either by typing them or sending a Voice Note.")
        return HTMLResponse(content=str(resp), media_type="application/xml")

    session_id = uuid.uuid4().hex[:6]

    # Pass to background task
    background_tasks.add_task(
        background_whatsapp_pipeline,
        sender_number,
        session_id,
        text_body,
        image_urls,
        audio_url
    )

    resp = MessagingResponse()
    resp.message("🎬 Photos & Instructions received! AI is processing...")
    return HTMLResponse(content=str(resp), media_type="application/xml")