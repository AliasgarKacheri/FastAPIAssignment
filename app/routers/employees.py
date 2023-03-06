from typing import Optional
from fastapi import Depends, UploadFile, File, APIRouter

from sqlalchemy.orm import Session
from app import schemas
from app.database.database import get_db
from app.security import oauth2
from app.repository import employee

DEFAULT_PASSWORD = "Test@12345"

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post("/bulk-upload-employees")
def bulk_upload_employees(file: UploadFile = File(), db: Session = Depends(get_db)):
    return employee.bulk_upload_employees(file, db)


@router.get('/')
async def all_employees(first_name: Optional[str] = None, last_name: Optional[str] = None, email: Optional[str] = None,
                        date_of_joining: Optional[str] = None, db: Session = Depends(get_db),
                        current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    return await employee.all_employees(first_name, last_name, email, date_of_joining, db, current_user)


@router.get('/{email}')
async def get_employee(email: str, db: Session = Depends(get_db),
                       current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    return await employee.get_employee(email, db, current_user)


@router.put('/{email}')
async def update_employee(email: str, request: schemas.UpdateEmployee, db: Session = Depends(get_db),
                          current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    return await employee.update_employee(email, request, db, current_user)


@router.delete('/{email}')
async def delete_employee(email: str, db: Session = Depends(get_db),
                          current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    return await employee.delete_employee(email, db, current_user)
