from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class VideoFile(Base):
    __tablename__ = "video_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    filepath: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    folder: Mapped[str] = mapped_column(Text, nullable=False)
    extension: Mapped[str] = mapped_column(String(32), nullable=False)

    filesize_mb: Mapped[float] = mapped_column(Float, default=0.0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    frame_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    codec_note: Mapped[str] = mapped_column(String(128), default="")
    scan_status: Mapped[str] = mapped_column(String(64), default="ok")
    error_message: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    shot_segments: Mapped[list["ShotSegment"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )


class ShotSegment(Base):
    __tablename__ = "shot_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    video_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("video_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)

    detector_name: Mapped[str] = mapped_column(String(128), default="fixed_segment_v001")
    detector_version: Mapped[str] = mapped_column(String(32), default="0.3.0")

    status: Mapped[str] = mapped_column(String(64), default="pending_vision")
    note: Mapped[str] = mapped_column(Text, default="")

    # Future Vision Module will fill these columns.
    blur_score: Mapped[float] = mapped_column(Float, default=0.0)
    shake_score: Mapped[float] = mapped_column(Float, default=0.0)
    exposure_score: Mapped[float] = mapped_column(Float, default=0.0)
    motion_score: Mapped[float] = mapped_column(Float, default=0.0)
    beauty_score: Mapped[float] = mapped_column(Float, default=0.0)
    ai_keep_score: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    video: Mapped[VideoFile] = relationship(back_populates="shot_segments")
