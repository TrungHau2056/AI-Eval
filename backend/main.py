import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.frontend_api import router as frontend_router
from src.api.routers.crawl import router as crawl_router
from src.observability.langfuse import flush_langfuse
from src.api.routers.crawl import router as crawl_router



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("app")

app = FastAPI(title="AI Test Case Generator API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(frontend_router)
app.include_router(crawl_router)

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.on_event("shutdown")
def shutdown():
    flush_langfuse()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
