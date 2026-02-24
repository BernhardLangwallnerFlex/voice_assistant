from fastapi import FastAPI

from app.routers import auth, voice

app = FastAPI(title="Voice Command Backend")

app.include_router(voice.router)
app.include_router(auth.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
