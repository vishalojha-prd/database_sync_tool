from fastapi import FastAPI
from app.routes import compare, update

app = FastAPI()

# Include Routes
app.include_router(compare.router)
app.include_router(update.router)

@app.get("/")
def root():
    return {"message": "Database Sync Tool Backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
