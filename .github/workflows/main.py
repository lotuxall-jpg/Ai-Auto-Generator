import json
import os
import subprocess
import re
import random
from datetime import datetime
from pathlib import Path

# ------------------------------
# 1. Setup logging & directories
# ------------------------------
LOG_FILE = "posted_log.json"
OUTPUT_DIR = "output"
ASSETS_DIR = "assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

def load_log():
    """Load existing log; return empty list if missing/invalid."""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except json.JSONDecodeError:
        print(f"Warning: {LOG_FILE} is corrupted. Starting fresh.")
        if os.path.exists(LOG_FILE):
            os.rename(LOG_FILE, f"{LOG_FILE}.bak")
        return []

def save_log(log_data):
    """Save log data to file."""
    with open(LOG_FILE, 'w') as f:
        json.dump(log_data, f, indent=2)

# ------------------------------
# 2. AI script generation
# ------------------------------
def generate_script():
    try:
        import openai
    except ImportError:
        return "This is a sample AI-generated clip. OpenAI integration not installed."

    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        return "This is a sample AI-generated clip. Please set your OpenAI API key."

    prompt = (
        "Write a short, engaging script for a 60-second TikTok/YouTube Shorts video. "
        "The topic should be interesting and viral-friendly. Keep it concise and punchy. "
        "Start with a hook, then give 3 quick facts or tips, and end with a call to action. "
        "The script should be suitable for a text-to-speech voice. Output only the script text."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative scriptwriter for viral short videos."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return "Did you know? AI can now create entire videos automatically. This is a demo clip. Set up your OpenAI key to generate unique scripts."

# ------------------------------
# 3. Text-to-Speech with edge-tts
# ------------------------------
def text_to_speech(text, output_audio):
    voice = "en-US-JennyNeural"  # natural female voice
    cmd = ["edge-tts", "--voice", voice, "--text", text, "--write-media", output_audio]
    try:
        subprocess.run(cmd, check=True)
        print(f"Audio generated: {output_audio}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"edge-tts failed: {e}")
        return False

# ------------------------------
# 4. Audio mixing (voice + music + sound effects)
# ------------------------------
def mix_audio(voice_path, music_path, sfx_paths, output_mixed):
    from moviepy.editor import AudioFileClip, CompositeAudioClip
    from moviepy.audio.fx import volumex

    # Load voice
    voice = AudioFileClip(voice_path)
    duration = voice.duration

    # Load background music, loop if shorter
    if os.path.exists(music_path):
        music = AudioFileClip(music_path).volumex(0.3)  # lower volume
        if music.duration < duration:
            music = music.loop(duration=duration)
        else:
            music = music.subclip(0, duration)
    else:
        music = None

    # List of audio clips: voice + music (if any)
    clips = [voice]
    if music:
        clips.append(music)

    # Add sound effects at specific times (e.g., at the beginning and after each tip)
    # For simplicity, we'll add them at 0s, 15s, 30s, 45s if we have sfx files.
    if sfx_paths:
        for sfx_path, time in sfx_paths:
            if os.path.exists(sfx_path):
                sfx = AudioFileClip(sfx_path).volumex(1.2)
                sfx = sfx.set_start(time)
                clips.append(sfx)

    # Composite all
    composite = CompositeAudioClip(clips)
    composite.write_audiofile(output_mixed, codec='aac')
    return True

# ------------------------------
# 5. Video creation with dynamic effects
# ------------------------------
def create_video_with_effects(audio_path, output_video, script_text):
    from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, TextClip, concatenate_videoclips, vfx
    import numpy as np

    # Load audio to get duration
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    # --- Background ---
    # Try to use a stock video; if not, fallback to a black background with Ken Burns zoom
    bg_path = os.path.join(ASSETS_DIR, "background.mp4")
    if os.path.exists(bg_path):
        bg = VideoFileClip(bg_path).subclip(0, duration).resize(height=1920)
        # Apply Ken Burns zoom (slow zoom in)
        def zoom_in(t):
            # zoom factor from 1.0 to 1.2 over duration
            return 1 + 0.2 * (t / duration)
        bg = bg.resize(lambda t: zoom_in(t))
    else:
        # Solid color background with a subtle gradient? For simplicity, use black
        bg = ColorClip(size=(1080, 1920), color=(0,0,0)).set_duration(duration)

    # --- Split script into sentences for captions ---
    sentences = re.split(r'(?<=[.!?])\s+', script_text.strip())
    # Remove empty sentences
    sentences = [s for s in sentences if s]

    # Determine timing for each sentence based on audio duration
    # Rough estimate: assume each word takes ~0.3 sec; we'll use a simple linear distribution.
    # A better approach would be to get word timings from TTS, but edge-tts doesn't give them.
    # So we'll distribute sentences proportionally to their character count.
    total_chars = sum(len(s) for s in sentences)
    timings = []
    current_time = 0.0
    for s in sentences:
        char_ratio = len(s) / total_chars if total_chars > 0 else 1/len(sentences)
        seg_duration = char_ratio * duration
        timings.append((s, current_time, current_time + seg_duration))
        current_time += seg_duration

    # --- Create text clips with animation (fade in/out) ---
    text_clips = []
    for text, start, end in timings:
        # Wrap text to fit screen width (optional)
        wrapped = text  # simple; could use textwrap
        # TextClip with bigger font and bold
        txt = TextClip(wrapped, fontsize=60, color='white', font='Arial', stroke_color='black', stroke_width=2)
        txt = txt.set_position(('center', 'center')).set_start(start).set_duration(end - start)
        # Add fade in/out
        txt = txt.crossfadein(0.5).crossfadeout(0.5)
        text_clips.append(txt)

    # --- Optional: Add a title at the beginning (e.g., "AI FACTS") ---
    title = TextClip("AI FACTS", fontsize=90, color='yellow', font='Arial-Bold', stroke_color='black', stroke_width=3)
    title = title.set_position(('center', 'top')).set_duration(2).crossfadein(0.5).crossfadeout(0.5)
    text_clips.append(title)

    # --- Composite everything ---
    final = CompositeVideoClip([bg] + text_clips)
    final = final.set_audio(audio)
    final = final.set_duration(duration)

    # Write video
    final.write_videofile(output_video, fps=24, codec='libx264', audio_codec='aac', threads=4)
    print(f"Video created: {output_video}")
    return True

# ------------------------------
# 6. Upload stubs (replace with real API calls)
# ------------------------------
def upload_to_youtube(video_path, title, description, tags):
    print(f"[YouTube] Would upload: {title}")
    # TODO: implement YouTube upload using google-api-python-client
    return True

def upload_to_tiktok(video_path, description):
    print(f"[TikTok] Would upload: {description}")
    # TODO: implement TikTok upload using official API or tiktok-uploader
    return True

# ------------------------------
# 7. Main workflow
# ------------------------------
def main():
    # Load previous posts log
    posted = load_log()
    print(f"Loaded {len(posted)} previously posted items.")

    # 1. Generate script
    script = generate_script()
    print("Script generated:\n", script)

    # 2. Generate voiceover
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_audio = os.path.join(OUTPUT_DIR, f"voice_{timestamp}.mp3")
    if not text_to_speech(script, raw_audio):
        print("Failed to generate voiceover. Exiting.")
        return

    # 3. Prepare audio effects (music + sfx)
    music_path = os.path.join(ASSETS_DIR, "background_music.mp3")
    sfx_paths = []
    # Example: add pop sound at beginning and after 10 sec if files exist
    pop_sfx = os.path.join(ASSETS_DIR, "sound_effect_pop.wav")
    if os.path.exists(pop_sfx):
        sfx_paths.append((pop_sfx, 0.0))
        sfx_paths.append((pop_sfx, 10.0))
    mixed_audio = os.path.join(OUTPUT_DIR, f"mixed_audio_{timestamp}.mp3")
    mix_audio(raw_audio, music_path, sfx_paths, mixed_audio)

    # 4. Create video with effects
    video_path = os.path.join(OUTPUT_DIR, f"clip_{timestamp}.mp4")
    if not create_video_with_effects(mixed_audio, video_path, script):
        print("Failed to create video. Exiting.")
        return

    # 5. Upload
    title = "AI Generated Clip - " + timestamp
    description = script[:200] + "..." if len(script) > 200 else script
    tags = ["ai", "clip", "viral"]
    youtube_success = upload_to_youtube(video_path, title, description, tags)
    tiktok_success = upload_to_tiktok(video_path, description)

    # 6. Log if any upload succeeded
    if youtube_success or tiktok_success:
        posted.append({
            "video": video_path,
            "title": title,
            "youtube_success": youtube_success,
            "tiktok_success": tiktok_success,
            "timestamp": datetime.now().isoformat()
        })
        save_log(posted)
        print("Log updated.")
    else:
        print("Uploads failed, not logged.")

if __name__ == "__main__":
    main()
