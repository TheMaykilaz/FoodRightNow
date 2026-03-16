from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from controllers.api_routers import router

app = FastAPI(title="Delivery Management System API")

# Мінімальний глобальний exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "Внутрішня помилка сервера", "details": str(exc)},
    )

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    # Запуск сервера
    uvicorn.run(app, host="0.0.0.0", port=8000)