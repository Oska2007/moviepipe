import asyncio
import logging
import os
from dataclasses import dataclass

from app.database import SessionLocal
from app.models import Job
from app.downloader.direct import download_direct
from app.downloader.torrent import download_torrent
from app.analyzer.video import analyze_video
from app.converter.video import convert_to_mp4
from app.subtitles.generator import generate_subtitles
from app.subtitles.embedder import embed_subtitles

logger = logging.getLogger(__name__)

@dataclass(order=True)
class QueueItem:
    priority: int
    job_id: str

class JobQueue:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[QueueItem] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    def start(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())

    async def enqueue(self, job_id: str, priority: int = 100) -> None:
        await self.queue.put(QueueItem(priority=priority, job_id=job_id))

    async def _worker(self) -> None:
        while True:
            item = await self.queue.get()
            try:
                await self._process(item.job_id)
            except Exception:
                logger.exception("Queue worker failed for job %s", item.job_id)
            finally:
                self.queue.task_done()

    async def _process(self, job_id: str) -> None:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if not job or job.status == "CANCELLED":
                return

            try:
                job.status = "DOWNLOADING"
                db.commit()

                os.makedirs("media", exist_ok=True)
                job_dir = os.path.join("media", job.id)
                os.makedirs(job_dir, exist_ok=True)

                if job.source_type == "url":
                    filepath = await download_direct(job.source, job_dir)
                elif job.source_type in ["magnet", "torrent"]:
                    loop = asyncio.get_running_loop()
                    filepath = await loop.run_in_executor(
                        None, download_torrent, job.source, job_dir, job.torrent_file_index
                    )
                else:
                    raise ValueError("Upload not implemented yet")

                job.status = "DOWNLOADED"
                job.original_filename = os.path.basename(filepath)
                job.source_size = os.path.getsize(filepath)
                db.commit()

                job.status = "ANALYZING"
                db.commit()

                info = analyze_video(filepath)
                job.video_codec = info["video_codec"]
                job.audio_codec = info["audio_codec"]
                job.duration = info["duration"]
                db.commit()

                job.status = "CONVERTING"
                db.commit()

                output_filename = f"{job.id}_converted.mp4"
                converted_path = os.path.join(job_dir, output_filename)
                
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None, convert_to_mp4, filepath, converted_path, info["video_codec"], info["audio_codec"]
                )
                db.commit()

                job.status = "GENERATING_SUBTITLES"
                job.english_subtitle_status = "GENERATING"
                job.sinhala_subtitle_status = "GENERATING"
                db.commit()

                eng_srt, sin_srt = await loop.run_in_executor(None, generate_subtitles, converted_path, job_dir)
                
                job.english_subtitle_status = "COMPLETED"
                job.sinhala_subtitle_status = "COMPLETED"
                db.commit()

                job.status = "EMBEDDING_SUBTITLES"
                db.commit()

                if job.custom_output_name:
                    safe_name = "".join([c for c in job.custom_output_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
                    final_filename = f"{safe_name}.mp4"
                else:
                    final_filename = f"{job.id}_final.mp4"
                    
                final_path = os.path.join(job_dir, final_filename)
                
                await loop.run_in_executor(None, embed_subtitles, converted_path, eng_srt, sin_srt, final_path)

                job.output_filename = final_filename
                job.output_size = os.path.getsize(final_path)
                db.commit()

                job.status = "COMPLETED"
                job.error_message = "Processing finished successfully."
                db.commit()

            except Exception as e:
                job.status = "FAILED"
                job.error_message = str(e)
                db.commit()
                logger.error(f"Job {job_id} failed: {e}")

job_queue = JobQueue()