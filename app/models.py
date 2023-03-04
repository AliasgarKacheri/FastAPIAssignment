from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)


class Employee(Base):
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(30), nullable=False)
    last_name = Column(String(30), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String, default="Test@12345")
    yrs_of_experience = Column(Integer, nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'))
    date_of_joining = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(50))
    updated_by = Column(String(50))
    is_active = Column(Boolean, default=False)
