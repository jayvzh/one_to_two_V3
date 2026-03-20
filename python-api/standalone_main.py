"""
PyInstaller standalone entry point for OneToTwo API.
This script is designed to be packaged with PyInstaller.
"""
import sys
import os
from pathlib import Path

def get_base_path():
    """Get the base path for the application (for code/modules)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent

def get_data_path():
    """Get the data path for persistent data (cache, models, reports).
    
    This returns the application root directory (where the main exe is located),
    not _MEIPASS or the resources directory.
    This ensures cache and other data persist across runs.
    """
    if getattr(sys, 'frozen', False):
        exe_path = Path(sys.executable)
        if exe_path.parent.name == 'resources':
            return exe_path.parent.parent
        return exe_path.parent
    return Path(__file__).parent

def setup_paths():
    """Setup Python paths for the application."""
    base_path = get_base_path()

    paths_to_add = [
        str(base_path),
        str(base_path / "core"),
        str(base_path / "data"),
        str(base_path / "ml"),
        str(base_path / "pipeline"),
        str(base_path / "schemas"),
        str(base_path / "routes"),
        str(base_path / "services"),
    ]

    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)

    return base_path

def main():
    """Main entry point for the standalone API server."""
    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles

    base_path = setup_paths()
    data_path = get_data_path()

    os.chdir(data_path)

    print(f"[OneToTwo API] Base path (code): {base_path}")
    print(f"[OneToTwo API] Data path (persistent): {data_path}")
    print(f"[OneToTwo API] Working directory: {os.getcwd()}")

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print("[OneToTwo API] Starting OneToTwo API Server...")
        print(f"[OneToTwo API] Working directory: {data_path}")
        yield
        print("[OneToTwo API] Shutting down OneToTwo API Server...")

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

    reports_dir = data_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")

    images_dir = reports_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")

    datasets_dir = data_path / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    
    cache_dir = datasets_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    models_dir = datasets_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    snapshots_dir = datasets_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

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

    from routes import router as api_router
    app.include_router(api_router)

    host = os.environ.get("ONETOTWO_API_HOST", "127.0.0.1")
    port = int(os.environ.get("ONETOTWO_API_PORT", "8000"))

    print(f"[OneToTwo API] Starting server on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )

if __name__ == "__main__":
    main()
