import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from main import process_video

DOWNLOADS_DIR = "/downloads"

class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        file_path = event.src_path
        
        # බාගැනීම ඉවර වෙනකම් ඉන්න (ෆයිල් එකේ සයිස් එක වැඩි නොවන තෙක්)
        if file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
            print(f"New video detected: {file_path}")
            previous_size = -1
            while True:
                try:
                    current_size = os.path.getsize(file_path)
                    if current_size == previous_size:
                        break # බාගැනීම ඉවරයි
                    previous_size = current_size
                    time.sleep(5)
                except FileNotFoundError:
                    return # ෆයිල් එක මැකිලා ඇත්නම්

            print(f"Download complete, sending to queue: {file_path}")
            # මේක තමයි අපේ ප්‍රධාන ක්‍රියාවලියට (Celery) යවන්නේ
            process_video.delay(file_path)

if __name__ == "__main__":
    event_handler = VideoHandler()
    observer = Observer()
    observer.schedule(event_handler, DOWNLOADS_DIR, recursive=False)
    observer.start()
    print(f"Watching directory: {DOWNLOADS_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()