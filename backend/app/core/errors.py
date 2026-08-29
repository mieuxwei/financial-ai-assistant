class AppError(Exception):
    status_code = 400
    code = "application_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ExpiredOperationError(AppError):
    status_code = 409
    code = "operation_expired"


class InvalidRequestError(AppError):
    status_code = 400
    code = "invalid_request"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
