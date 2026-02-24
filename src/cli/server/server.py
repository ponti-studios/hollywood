from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer

from snakesss.cli.server.routers.media import audio_router, vision_router
from snakesss.cli.server.routers.chat_router import router as chat_router
from snakesss.cli.server.routers.crew_router import router as crew_router
from snakesss.cli.server.routers.task_router import router as task_router
from snakesss.cli.server.routers.tool_router import router as tool_router
from snakesss.cli.server.routers.scraper_router import router as scraper_router

app = FastAPI()

# Allow CORS for all origins for simplicity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Routers
app.include_router(chat_router)
app.include_router(tool_router)
app.include_router(crew_router)
app.include_router(task_router)
app.include_router(audio_router.router, prefix="/media")
app.include_router(vision_router.router, prefix="/vision")
# Include the new scraper router with no prefix so the route is /scrape
app.include_router(scraper_router)


@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(request, exc):
    content = {
        "detail": exc.errors(),
    }
    print(content)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=content)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request, exc):
    content = {
        "detail": exc.errors(),
    }
    print(content)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=content)


# Root
@app.get("/info")
async def root():
    return {"message": "🐍🐍🐍"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Snakesss API",
        version="0.0.1",
        summary="Snakesss API",
        description="Snakesss API",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {"url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"}
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
