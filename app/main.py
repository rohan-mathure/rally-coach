from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import init_db
from app.routers import upload, sessions, shots, video


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Rally Coach", lifespan=lifespan)

app.include_router(upload.router)
app.include_router(sessions.router)
app.include_router(shots.router)
app.include_router(video.router)

_static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_static), name="static")


@app.get("/")
async def root():
    return FileResponse(_static / "index.html")


@app.get("/session")
async def session_page():
    return FileResponse(_static / "session.html")
