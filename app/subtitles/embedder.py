import subprocess
import os

def embed_subtitles(video_path: str, eng_srt: str, sin_srt: str, output_path: str):
    max_threads = os.getenv("MAX_CPU_THREADS", "2")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", eng_srt,
        "-i", sin_srt,
        "-map", "0:v", "-map", "0:a", "-map", "1", "-map", "2",
        "-c:v", "copy", "-c:a", "copy",
        "-c:s", "mov_text",
        "-threads", max_threads,
        "-metadata:s:s:0", "language=eng",
        "-metadata:s:s:0", "title=English",
        "-metadata:s:s:0", "default=1", 
        "-metadata:s:s:1", "language=sin",
        "-metadata:s:s:1", "title=Sinhala",
        "-metadata:s:s:1", "default=0",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Subtitle embedding failed: {result.stderr}")
    
    return output_path