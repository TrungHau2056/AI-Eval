from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import input, intents, personas, prompts, export, state

app = FastAPI(title="AI Test Case Generator API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(input.router)
app.include_router(intents.router)
app.include_router(personas.router)
app.include_router(prompts.router)
app.include_router(export.router)
app.include_router(state.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
