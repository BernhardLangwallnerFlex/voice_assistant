from fastapi import Header, HTTPException

SECRET = "d69eac9b0dd6174c5166830a2a487d48d1ad1da814579bd48305b1a4b30c24ab"

@app.post("/voice")
async def voice_endpoint(payload: VoiceInput, authorization: str = Header(None)):

    if authorization != f"Bearer {SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    print("Authorized request:", payload.text)

    return {"status": "ok"}