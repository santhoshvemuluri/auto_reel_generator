# 🎬 Auto Reel Studio PRO

A fully automated, AI-driven SaaS backend that generates high-quality vertical social media videos (Instagram Reels / YouTube Shorts) directly from WhatsApp messages and voice notes.

## 🚀 Features
*   **WhatsApp-First Interface:** Users send photos and a voice note (or text) to a Twilio WhatsApp bot.
*   **Multimodal AI Parsing:** Uses Google Gemini to listen to audio voice notes, extract vehicle/property details, and determine user intent.
*   **Virtual Showroom (AI Background Removal):** Automatically strips messy backgrounds from uploaded images using embg and places subjects in a high-end 3D studio gradient.
*   **Dynamic Scripting:** Generates highly punctuated, high-retention scripts in Telugu (Tenglish), Hindi (Hinglish), and English (Indian accent).
*   **Premium AI Voiceovers:** Synthesizes studio-quality female voiceovers via Sarvam AI.
*   **Cinematic B-Roll:** Automatically fetches official YouTube trailers (via yt-dlp) for video hooks.
*   **Programmatic Rendering:** Uses Remotion (React) to compile audio, synced subtitles, dynamic scaling animations, custom branding, and urgency tags into a final MP4.

## 🛠️ Tech Stack
*   **Backend:** Python, FastAPI
*   **Video Engine:** Remotion, React, Node.js
*   **AI Services:** Google Gemini 1.5 Flash (Multimodal), Sarvam AI (TTS)
*   **Media Processing:** embg, yt-dlp, Pillow
*   **Integrations:** Twilio Sandbox for WhatsApp, Ngrok for webhooks

## ⚙️ Setup & Installation
1. Clone the repository.
2. Install Python dependencies: pip install -r backend/requirements.txt
3. Install Node.js dependencies: cd video-engine && npm install
4. Set up your .env file with your API keys (Gemini, Sarvam, Twilio).

## 🚦 Usage
1. Start the FastAPI server: uvicorn app:app --reload --port 8000
2. Expose the local server: 
grok http 8000
3. Link the Ngrok URL to your Twilio WhatsApp Sandbox webhook.
4. Send 2-3 photos and a voice note to your Twilio number to generate a reel!
