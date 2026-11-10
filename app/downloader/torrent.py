import subprocess
import os
import logging
import tempfile

logger = logging.getLogger(__name__)

def get_torrent_files(source: str) -> list:
    """Torrent හෝ Magnet එකේ තියෙන ෆයිල්ස් ලිස්ට් එක ගන්නවා"""
    try:
        # 1. පළවෙලාවට බලමු මේක Magnet link එකක්ද කියලා
        if source.startswith("magnet:"):
            logger.info("Magnet link detected. Fetching metadata...")
            # Magnet link එකක් නම්, metadata (.torrent file) එක විතරක් ඩවුන්ලෝඩ් කරගන්නවා
            with tempfile.TemporaryDirectory() as tmpdir:
                cmd_meta = [
                    "aria2c",
                    "--dir", tmpdir,
                    "--bt-metadata-only=true",
                    "--bt-save-metadata=true",
                    "--follow-torrent=mem",
                    "--seed-time=0",
                    source
                ]
                res = subprocess.run(cmd_meta, capture_output=True, text=True, timeout=120)
                
                # Metadata ෆයිල් එක හොයාගන්නවා
                torrent_file = None
                for f in os.listdir(tmpdir):
                    if f.endswith(".torrent"):
                        torrent_file = os.path.join(tmpdir, f)
                        break
                        
                if not torrent_file:
                    raise RuntimeError("Could not fetch metadata from magnet link. Please check if the link is valid or if peers are available.")
                    
                # දැන් ඒ .torrent ෆයිල් එකෙන් ෆයිල් ලිස්ට් එක ගන්නවා
                logger.info(f"Metadata downloaded: {torrent_file}")
                return _parse_torrent_files(torrent_file)
        else:
            # .torrent ෆයිල් එකක් නම් කෙලින්ම ලිස්ට් එක ගන්නවා
            return _parse_torrent_files(source)
            
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout while fetching torrent metadata. Please try again (Magnet links may take time).")
    except Exception as e:
        logger.error(f"Error in get_torrent_files: {e}")
        raise

def _parse_torrent_files(torrent_source: str) -> list:
    """aria2c --show-files පාවිච්චි කරලා ෆයිල් ලිස්ට් එක parse කරනවා"""
    cmd = ["aria2c", "--show-files", torrent_source]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to read torrent metadata: {result.stderr}")
    
    files = []
    lines = result.stdout.splitlines()
    for line in lines:
        # aria2c output එකේ format එක: "  1|Filename.mp4|12345678|..."
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