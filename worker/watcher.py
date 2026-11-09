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
        
        # වීඩියෝ ෆයිල් එකක්ද බලනවා (ටොරන්ට් එක්ක එන .srt ෆයිල්ස් මඟහරිනවා)
        if file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
            print(f"New video detected: {file_path}")
            
            # Aria2 එකේ .aria2 ෆයිල් එක තියෙනකම් බලාගෙන ඉන්නවා (බාගැනීම ඉවර නැහැ)
            aria2_file = file_path + ".aria2"
            time.sleep(3) # ෆයිල් එක හැදෙන්න ටිකක් වෙලාව දෙන්න
            
            while os.path.exists(aria2_file):
                print(f"Still downloading... waiting for {os.path.basename(file_path)}")
                time.sleep(10) # තත්පර 10න් 10ට චෙක් කරනවා
                
            print(f"Download complete, sending to queue: {file_path}")
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