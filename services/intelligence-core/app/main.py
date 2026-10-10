import os
from dotenv import load_dotenv

# Load .env from the repo root and from this service folder before auth settings are read
_here = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_here, "..", "..", "..", ".env"))
load_dotenv(os.path.join(_here, "..", ".env"))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.auth import auth0
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    auth0.validate_config()
    init_db()
    yield


app = FastAPI(
    title="OTT Intelligence Platform Core",
    description="Mood-aware entertainment discovery and personalization API (Auth0-protected).",
    version="2.0.0",
    lifespan=lifespan
)

# The browser talks to the Next.js server (which proxies here), so CORS can stay tight.
# Set CORS_ORIGINS="http://localhost:3000,https://your-app.com" to allow direct calls.
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(router)



@app.get("/")
def root():
    return {"service": "OTT Intelligence Core", "docs": "/docs", "web_app": "http://localhost:3000"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "intelligence-core", "version": "2.0.0",
            "auth": "disabled (dev)" if auth0.AUTH_DISABLED else "auth0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
