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
        # print(f"DEBUG: Event detected for: {file_path}")
        
        # වීඩියෝ ෆයිල් එකක්ද බලනවා (ටොරන්ට් එක්ක එන .srt ෆයිල්ස් මඟහරිනවා)
        if file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
            print(f"New video detected: {file_path}")
            previous_size = -1
            while True:
                try:
                    current_size = os.path.getsize(file_path)
                    if current_size == previous_size:
                        break # බාගැනීම ඉවරයි (සයිස් එක වැඩි වෙනවා නැත්නම්)
                    previous_size = current_size
                    time.sleep(5)
                except FileNotFoundError:
                    return 

            print(f"Download complete, sending to queue: {file_path}")
            # Celery එකට යවනවා
            process_video.delay(file_path)

if __name__ == "__main__":
    event_handler = VideoHandler()
    observer = Observer()
    observer.schedule(event_handler, DOWNLOADS_DIR, recursive=True) # Recursive True!
    observer.start()
    print(f"Watching directory: {DOWNLOADS_DIR} (Recursive mode)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()