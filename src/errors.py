import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("buscaai")


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "message": message})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            "VALIDATION_ERROR",
            "Dados inválidos.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro inesperado ao processar %s %s", request.method, request.url.path)
        return _error_response(
            "INTERNAL_ERROR",
            "Erro interno do servidor.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
