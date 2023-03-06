import csv
from typing import Optional

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, status
from sqlalchemy import asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import schemas
from security import JWTtoken
from app.database.database import Base, get_db, engine
from app.security import oauth2, hashing
from app.database import models
import uvicorn
from app.routers import authenticator, employees
import codecs
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime

app = FastAPI()
Base.metadata.create_all(engine)
app.include_router(authenticator.router)
app.include_router(employees.router)

if __name__ == '__main__':
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
