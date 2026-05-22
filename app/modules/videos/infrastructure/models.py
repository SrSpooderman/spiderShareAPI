from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Float,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infrastructure.db.base import Base


class VideoModel(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    is_registered_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="0",
    )
    edited: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="pending",
    )
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aspect_ratio: Mapped[str | None] = mapped_column(String(8), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    favorite_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )

    category_assignments: Mapped[list["VideoCategoryAssignmentModel"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )
    tag_assignments: Mapped[list["VideoTagAssignmentModel"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )
    variants: Mapped[list["VideoVariantModel"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )


class VideoVariantModel(Base):
    __tablename__ = "video_variants"
    __table_args__ = (
        UniqueConstraint("video_id", "variant_type", name="uq_video_variants_video_type"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    video_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_type: Mapped[str] = mapped_column(String(32), nullable=False)
    codec: Mapped[str] = mapped_column(String(32), nullable=False)
    container: Mapped[str] = mapped_column(String(32), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    bitrate_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    video: Mapped[VideoModel] = relationship(back_populates="variants")


class VideoCategoryModel(Base):
    __tablename__ = "video_categories"
    __table_args__ = (UniqueConstraint("name", name="uq_video_categories_name"),)

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )


class VideoCategoryAssignmentModel(Base):
    __tablename__ = "video_category_assignments"
    __table_args__ = (
        UniqueConstraint(
            "video_id",
            "category_id",
            name="uq_video_category_assignments_video_category",
        ),
    )

    video_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("videos.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("video_categories.id", ondelete="CASCADE"),
        primary_key=True,
    )

    video: Mapped[VideoModel] = relationship(back_populates="category_assignments")
    category: Mapped[VideoCategoryModel] = relationship()


class VideoTagModel(Base):
    __tablename__ = "video_tags"
    __table_args__ = (UniqueConstraint("name", name="uq_video_tags_name"),)

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )


class VideoTagAssignmentModel(Base):
    __tablename__ = "video_tag_assignments"
    __table_args__ = (
        UniqueConstraint(
            "video_id",
            "tag_id",
            name="uq_video_tag_assignments_video_tag",
        ),
    )

    video_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("videos.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("video_tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

    video: Mapped[VideoModel] = relationship(back_populates="tag_assignments")
    tag: Mapped[VideoTagModel] = relationship()


class VideoFavoriteModel(Base):
    __tablename__ = "video_favorites"
    __table_args__ = (
        UniqueConstraint("video_id", "user_id", name="uq_video_favorites_video_user"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    video_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class VideoReactionModel(Base):
    __tablename__ = "video_reactions"
    __table_args__ = (
        UniqueConstraint(
            "video_id",
            "user_id",
            "reaction_type",
            name="uq_video_reactions_video_user_type",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    video_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )
