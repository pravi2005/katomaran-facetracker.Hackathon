"""Application-specific exception types.

Using explicit exception classes (instead of bare ``Exception``) lets callers
decide which failures are recoverable (e.g. a transient DB error) and which
must stop the program (e.g. a missing model file).
"""


class AppError(Exception):
    """Base class for all errors raised deliberately by this application."""


class ConfigError(AppError):
    """config.json is missing, unreadable, or contains invalid values."""


class SourceError(AppError):
    """The video file / RTSP stream cannot be opened or has been lost."""


class ModelLoadError(AppError):
    """A detection or recognition model could not be loaded."""


class RecognitionError(AppError):
    """Embedding generation failed for a specific face crop."""


class DatabaseError(AppError):
    """A SQLite operation failed."""


class IncompatibleEmbeddingError(DatabaseError):
    """Stored embeddings were produced by a different model/dimension."""


class ImageStorageError(AppError):
    """A face image could not be written to disk."""
