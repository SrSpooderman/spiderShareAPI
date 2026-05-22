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


class VideoFileTooLargeError(VideoUploadError):
    pass


class VideoDurationTooLongError(VideoUploadError):
    pass


class VideoUnsupportedMimeTypeError(VideoUploadError):
    pass
