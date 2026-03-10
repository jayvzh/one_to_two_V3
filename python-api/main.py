from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys
import os

V2_DIR = Path(__file__).parent.parent / "one_to_two_V2"
API_DIR = Path(__file__).parent

if str(V2_DIR) not in sys.path:
    sys.path.insert(0, str(V2_DIR))

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

os.chdir(V2_DIR)

from routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting OneToTwo API Server...")
    print(f"Working directory: {V2_DIR}")
    print(f"API directory: {API_DIR}")
    yield
    print("Shutting down OneToTwo API Server...")


app = FastAPI(
    title="OneToTwo API",
    description="一进二策略分析系统 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

reports_dir = V2_DIR / "reports"
reports_dir.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")

images_dir = reports_dir / "images"
images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "detail": "Internal server error",
        },
    )


@app.get("/")
async def root():
    return {
        "name": "OneToTwo API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(Path(__file__).parent)],
    )
