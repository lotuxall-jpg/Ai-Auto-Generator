import os
import datetime

def create_test_video():
    try:
        from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
    except ImportError:
        print("moviepy not installed")
        return False

    # Create a black clip of 10 seconds
    video = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=10)
    # Add a text clip
    txt = TextClip("AI Clip Test", fontsize=70, color='white', stroke_color='black', stroke_width=2)
    txt = txt.set_position('center').set_duration(10)
    final = CompositeVideoClip([video, txt])

    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

    # Save video
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"output/test_{timestamp}.mp4"
    final.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
    print(f"Video created: {output_path}")
    return True

if __name__ == "__main__":
    create_test_video()
