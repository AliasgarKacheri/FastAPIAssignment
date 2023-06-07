from fastapi import FastAPI
from database.database import Base, engine
from database import models
import uvicorn
from routers import authenticator, employees

app = FastAPI()
models.Base.metadata.create_all(engine)
app.include_router(authenticator.router)
app.include_router(employees.router)

# if __name__ == '__main__':
#     uvicorn.run("main:app", host="localhost", port=8000, reload=True)
