from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, validator
import re

regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'


class Role(Enum):
    USER = 'USER'
    ADMIN = 'ADMIN'


class Employee(BaseModel):
    first_name: str
    last_name: Optional[str]
    email: str
    yrs_of_experience: int
    role: Optional[Role] = Role.USER

    @validator("first_name")
    def validate_first_name(cls, v):
        if len(v) < 3:
            raise ValueError("First name must be at least 3 characters long")
        if len(v) > 30:
            raise ValueError("First name must be at most 30 characters long")
        return v

    @validator("last_name")
    def validate_last_name(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError("Last name must be at least 3 characters long")
        if v is not None and len(v) > 30:
            raise ValueError("Last name must be at most 30 characters long")
        return v

    @validator("yrs_of_experience")
    def validate_yrs_of_experience(cls, v):
        if v < 0:
            raise ValueError("yrs_of_experience must be positive integer")
        return v

    @validator("email")
    def validate_email(cls, v):
        if not re.fullmatch(regex, v):
            raise ValueError("email is invalid")
        return v.lower()