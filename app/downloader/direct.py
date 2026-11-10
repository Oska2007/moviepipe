import httpx
import os

async def download_direct(url: str, dest_dir: str) -> str:
    if not url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL scheme. Only HTTP/HTTPS allowed.")

    filename = url.split("/")[-1].split("?")[0] or "downloaded_file.mp4"
    filepath = os.path.join(dest_dir, filename)

    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(filepath, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
    return filepath