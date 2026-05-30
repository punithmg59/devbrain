class DevBrainException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: str = "INTERNAL_ERROR",
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class AuthException(DevBrainException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, 401, "UNAUTHORIZED")


class NotFoundException(DevBrainException):
    def __init__(self, resource: str):
        super().__init__(f"{resource} not found", 404, "NOT_FOUND")


class RateLimitException(DevBrainException):
    def __init__(self):
        super().__init__("Rate limit exceeded", 429, "RATE_LIMIT_EXCEEDED")
