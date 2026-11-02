from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Football Club Hello")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def hello() -> Dict[str, str]:
    return {"message": "Hello World"}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}
