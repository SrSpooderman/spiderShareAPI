from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.videos.application.delete_video import DeleteVideo
from app.modules.videos.application.favorite_video import FavoriteVideo
from app.modules.videos.application.get_video import GetVideo
from app.modules.videos.application.list_videos import ListVideos
from app.modules.videos.application.process_video import ProcessVideo
from app.modules.videos.application.react_to_video import ReactToVideo
from app.modules.videos.application.upload_video import UploadVideo
from app.modules.videos.application.update_video import UpdateVideo
from app.modules.videos.domain.ports import VideoRepository, VideoStorage, VideoTranscoder
from app.modules.videos.infrastructure.repository import SqlAlchemyVideoRepository
from app.shared.infrastructure.db.session import get_db
from app.shared.infrastructure.providers.storage.video_storage import LocalVideoStorage
from app.shared.infrastructure.providers.storage.video_transcoder import FfmpegVideoTranscoder


def get_video_repository(db: Session = Depends(get_db)) -> VideoRepository:
    return SqlAlchemyVideoRepository(db)


def get_video_storage() -> VideoStorage:
    return LocalVideoStorage()


def get_video_transcoder() -> VideoTranscoder:
    return FfmpegVideoTranscoder()


def get_list_videos(
    video_repository: VideoRepository = Depends(get_video_repository),
) -> ListVideos:
    return ListVideos(video_repository)


def get_get_video(
    video_repository: VideoRepository = Depends(get_video_repository),
) -> GetVideo:
    return GetVideo(video_repository)


def get_update_video(
    video_repository: VideoRepository = Depends(get_video_repository),
) -> UpdateVideo:
    return UpdateVideo(video_repository)


def get_upload_video(
    video_repository: VideoRepository = Depends(get_video_repository),
    video_storage: VideoStorage = Depends(get_video_storage),
) -> UploadVideo:
    return UploadVideo(video_repository, video_storage)


def get_process_video(
    video_repository: VideoRepository = Depends(get_video_repository),
    video_transcoder: VideoTranscoder = Depends(get_video_transcoder),
) -> ProcessVideo:
    return ProcessVideo(video_repository, video_transcoder)


def get_delete_video(
    video_repository: VideoRepository = Depends(get_video_repository),
    video_storage: VideoStorage = Depends(get_video_storage),
) -> DeleteVideo:
    return DeleteVideo(video_repository, video_storage)


def get_favorite_video(
    video_repository: VideoRepository = Depends(get_video_repository),
) -> FavoriteVideo:
    return FavoriteVideo(video_repository)


def get_react_to_video(
    video_repository: VideoRepository = Depends(get_video_repository),
) -> ReactToVideo:
    return ReactToVideo(video_repository)
