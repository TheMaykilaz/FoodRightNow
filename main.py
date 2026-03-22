from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime, timezone
from controllers.api_routers import router
app = FastAPI(title="Delivery Management System API")

# Функція для генерації стандартного формату помилки
def create_error_format(status_code: int, message: str, path: str):
    return JSONResponse(
        status_code=status_code,
        content={
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": status_code,
            "message": message,
            "path": path
        }
    )

# Аналог @ExceptionHandler для HTTP помилок (наприклад, 404, 400)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return create_error_format(exc.status_code, exc.detail, request.url.path)

# Аналог @ExceptionHandler для помилок валідації (наприклад, кривий JSON)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return create_error_format(422, "Помилка валідації даних", request.url.path)

# Глобальний перехоплювач для 500 Internal Server Error
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return create_error_format(500, "Внутрішня помилка сервера", request.url.path)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    # Запуск сервера
    uvicorn.run(app, host="0.0.0.0", port=8000)