from fastapi import FastAPI
from .routers import llm

app = FastAPI()
app.include_router(llm.router)

@app.get("/")
async def root():
    return {"message": "Hello World!"}
