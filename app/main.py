from fastapi import FastAPI

from app.routers import auth, voice, voice_command

app = FastAPI(title="Voice Command Backend")

app.include_router(voice.router)
app.include_router(auth.router)
app.include_router(voice_command.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
