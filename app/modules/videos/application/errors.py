from dataclasses import dataclass


class VideoNotFoundError(Exception):
    pass


class VideoPermissionError(Exception):
    pass


class VideoReactionLimitError(Exception):
    pass


class VideoUploadError(Exception):
    pass


class VideoFileEmptyError(VideoUploadError):
    pass


@dataclass
class VideoFileTooLargeError(VideoUploadError):
    size_bytes: int | None = None
    limit_bytes: int | None = None


class VideoDurationTooLongError(VideoUploadError):
    pass


class VideoUnsupportedMimeTypeError(VideoUploadError):
    pass
