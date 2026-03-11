"""
PyInstaller standalone entry point for OneToTwo API.
This script is designed to be packaged with PyInstaller.
"""
import sys
import os
from pathlib import Path

def get_base_path():
    """Get the base path for the application."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent

def setup_paths():
    """Setup Python paths for the application."""
    base_path = get_base_path()
    
    v2_path = base_path / "one_to_two_V2"
    api_path = base_path / "python-api"
    
    paths_to_add = [
        str(base_path),
        str(v2_path),
        str(api_path),
        str(v2_path / "src"),
        str(v2_path / "src" / "core"),
        str(v2_path / "src" / "data"),
        str(v2_path / "src" / "model"),
        str(v2_path / "src" / "pipeline"),
        str(v2_path / "src" / "utils"),
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    return base_path, v2_path

def main():
    """Main entry point for the standalone API server."""
    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    
    base_path, v2_path = setup_paths()
    
    os.chdir(v2_path)
    
    print(f"[OneToTwo API] Base path: {base_path}")
    print(f"[OneToTwo API] Working directory: {v2_path}")
    
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print("[OneToTwo API] Starting OneToTwo API Server...")
        print(f"[OneToTwo API] Working directory: {v2_path}")
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
    
    reports_dir = v2_path / "reports"
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
