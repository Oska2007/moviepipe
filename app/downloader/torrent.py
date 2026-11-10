import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def get_torrent_files(source: str) -> list:
    try:
        cmd = ["aria2c", "--show-files", source]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to read torrent metadata: {result.stderr}")
        
        files = []
        lines = result.stdout.splitlines()
        for line in lines:
            if "|" in line and not line.startswith("***") and not line.startswith(">>>"):
                parts = line.split("|")
                if len(parts) >= 3:
                    try:
                        idx = int(parts[0].strip())
                        name = parts[1].strip()
                        size = int(parts[2].strip())
                        files.append({"index": idx, "name": name, "size": size})
                    except ValueError:
                        continue
        return files
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout while fetching torrent metadata. Please try again.")

def download_torrent(source: str, dest_dir: str, file_index: int = None) -> str:
    cmd = [
        "aria2c",
        "--dir", dest_dir,
        "--seed-time=0",
        "--max-connection-per-server=4",
        "--bt-stop-timeout=300", 
        "--follow-torrent=mem",
    ]
    
    if file_index:
        cmd.append(f"--select-file={file_index}")
        
    cmd.append(source)
    
    process = subprocess.run(cmd, capture_output=True, text=True)

    if process.returncode != 0:
        raise RuntimeError(f"Torrent download failed: {process.stderr}")

    files = [os.path.join(dest_dir, f) for f in os.listdir(dest_dir) if not f.endswith(".aria2")]
    if not files:
        raise RuntimeError("No files downloaded from torrent")
    
    largest_file = max(files, key=os.path.getsize)
    return largest_file