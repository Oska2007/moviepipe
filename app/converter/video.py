import subprocess
import os

def convert_to_mp4(input_path: str, output_path: str, video_codec: str, audio_codec: str):
    max_threads = os.getenv("MAX_CPU_THREADS", "2")
    
    cmd = ["ffmpeg", "-y", "-i", input_path]

    if video_codec == "h264":
        cmd.extend(["-c:v", "copy"])
    else:
        cmd.extend([
            "-c:v", "libx264", 
            "-crf", "23", 
            "-preset", "veryfast", 
            "-pix_fmt", "yuv420p",
            "-threads", max_threads
        ])

    if audio_codec == "aac":
        cmd.extend(["-c:a", "copy"])
    else:
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])

    cmd.extend(["-movflags", "+faststart", output_path])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")

    return output_path