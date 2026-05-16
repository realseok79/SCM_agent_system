from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "SCM Mock API Server Running"}

@app.get("/inventory")
def get_inventory():
    return {"items": [{"id": 1, "name": "CPU", "stock": 100}]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
