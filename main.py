from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


# Input data from API for the agent to process
class InputData(BaseModel):
    pass


@app.get("/")
def read_root():
    return {"Hello": "World"}
