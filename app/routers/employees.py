from typing import Optional
from fastapi import Depends, UploadFile, File, APIRouter, status

from sqlalchemy.orm import Session
import schemas
from database.database import get_db
from security import oauth2
from repository import employee


router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post("/bulk-upload-employees", status_code=status.HTTP_200_OK)
def bulk_upload_employees(file: UploadFile = File(), db: Session = Depends(get_db)):
    return employee.bulk_upload_employees(file, db)


@router.get('/', status_code=status.HTTP_200_OK)
async def all_employees(first_name: Optional[str] = None, last_name: Optional[str] = None, email: Optional[str] = None,
                        date_of_joining: Optional[str] = None, db: Session = Depends(get_db),
                        current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    return await employee.all_employees(first_name, last_name, email, date_of_joining, db, current_user)


@router.get('/{email}', status_code=status.HTTP_200_OK)
async def get_employee(email: str, db: Session = Depends(get_db),
                       current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    return await employee.get_employee(email, db, current_user)


@router.put('/{email}', status_code=status.HTTP_200_OK)
async def update_employee(email: str, request: schemas.UpdateEmployee, db: Session = Depends(get_db),
                          current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    return await employee.update_employee(email, request, db, current_user)


@router.delete('/{email}', status_code=status.HTTP_200_OK)
async def delete_employee(email: str, db: Session = Depends(get_db),
                          current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    return await employee.delete_employee(email, db, current_user)
