from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True)
    source_type: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(Text)
    
    torrent_file_index: Mapped[int | None] = mapped_column(nullable=True)
    custom_output_name: Mapped[str | None] = mapped_column(String(512), nullable=True)

    original_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    output_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)

    source_size: Mapped[int | None] = mapped_column(nullable=True)
    output_size: Mapped[int | None] = mapped_column(nullable=True)

    video_codec: Mapped[str | None] = mapped_column(String(50), nullable=True)
    audio_codec: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration: Mapped[float | None] = mapped_column(nullable=True)

    english_subtitle_status: Mapped[str] = mapped_column(String(50), default="PENDING")
    sinhala_subtitle_status: Mapped[str] = mapped_column(String(50), default="PENDING")

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)