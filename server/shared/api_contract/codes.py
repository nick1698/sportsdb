# Keep codes stable: UI can map them to translations / UX.
# Use a single namespace to avoid random strings across services.


class ErrorCode:
    VALIDATION_ERROR = "PLATFORM_VALIDATION_ERROR"
    NOT_FOUND = "PLATFORM_NOT_FOUND"
    UNAUTHORIZED = "PLATFORM_UNAUTHORIZED"
    FORBIDDEN = "PLATFORM_FORBIDDEN"
    BAD_REQUEST = "PLATFORM_BAD_REQUEST"
    INTERNAL_ERROR = "PLATFORM_INTERNAL_ERROR"
