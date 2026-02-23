from fastapi import FastAPI

app = FastAPI(title="SportsDB API")

@app.get("/health")
def health():
    return {"status": "ok"}