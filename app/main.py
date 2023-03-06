import csv
from typing import Optional

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, status
from sqlalchemy import asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import schemas
from security import JWTtoken
from database import Base, engine, get_db
from app.security import oauth2, hashing
import models
import uvicorn
import codecs
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime

app = FastAPI()
Base.metadata.create_all(engine)

DEFAULT_PASSWORD = "Test@12345"


@app.post("/bulk-upload-employees")
def bulk_upload_employees(file: UploadFile = File(),
                          db: Session = Depends(get_db)):
    """
    Bulk upload employees using a CSV file. Returns number of employees added and ignored.
    """
    # Check file name
    if file.filename != "bulk_upload_employees.csv":
        raise HTTPException(status_code=400, detail="Invalid file name")

    # Check file format
    file_format = file.filename.split(".")[-1]
    if file_format not in ["csv", "xls", 'vnd.ms-excel']:
        raise HTTPException(status_code=400, detail="Invalid file format")

    # Process CSV file
    try:
        data = file.file
        csv_data = csv.DictReader(codecs.iterdecode(file.file, 'utf-8'))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid file content: {e}")

    employees_added = 0
    employees_ignored = 0
    # check if fields names are same as we want
    field_names = {"first_name", "last_name", "yrs_of_experience", "role", "email"}
    if len(csv_data.fieldnames) == len(field_names):
        for field in csv_data.fieldnames:
            if field not in field_names:
                raise HTTPException(status_code=400, detail=f"Invalid file header")
    for row in csv_data:
        try:
            employee_data = schemas.Employee(**row)
        except ValueError as e:
            employees_ignored += 1
            continue
        db_employee = employee_data.dict()
        db_employee["created_by"] = -1
        db_employee["updated_by"] = -1
        db_employee["password"] = hashing.Hash.bcrypt(DEFAULT_PASSWORD)
        db_employee["role"] = db.query(models.Role).filter_by(name=row["role"]).first()
        try:
            db_employee = models.Employee(**db_employee)
            db.add(db_employee)
            db.commit()
            db.refresh(db_employee)
        except IntegrityError as e:
            employees_ignored += 1
            continue
        employees_added += 1
    return {"status": "uploaded"}


@app.post('/login')
def login(request: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user_db = db.query(models.Employee).filter(models.Employee.email == request.username)
    user = user_db.first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Invalid Credentials")
    if not hashing.Hash.verify(user.password, request.password):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Incorrect password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Please update your password by going to this link localhost/update-password-first-time")
    access_token = JWTtoken.create_access_token(
        data={"sub": user.email, "role": user.role.name, "is_active": user.is_active})
    # update last_login
    user_db.update({"last_login": datetime.utcnow()})
    db.commit()
    return {"access_token": access_token, "token_type": "Bearer"}


@app.post('/update-password-first-time')
def update_password(request: schemas.LoginUser, db: Session = Depends(get_db)):
    user = db.query(models.Employee).filter(models.Employee.email == request.email)
    db_user = user.first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Invalid Credentials")
    if not db_user.is_active:
        try:
            employee = schemas.EmployeeUser(email=request.email, password=request.password)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        request_dict = request.dict()
        request_dict["updated_at"] = datetime.utcnow()
        request_dict["is_active"] = True
        request_dict["password"] = hashing.Hash.bcrypt(request_dict["password"])
        user.update(request_dict)
        db.commit()
        return {"status": "successfully updated password now you can login"}
    else:
        raise HTTPException(status_code=400, detail="Only First time login can update the password")


@app.get('/employees')
async def all_employees(first_name: Optional[str] = None, last_name: Optional[str] = None, email: Optional[str] = None,
                        date_of_joining: Optional[str] = None, db: Session = Depends(get_db),
                        current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    await check_for_activation(current_user)
    # Query the database for all employees
    query = db.query(models.Employee)
    if not first_name and last_name and email and date_of_joining:
        raise HTTPException(status_code=400,
                            detail="Please provide any one field")

    # Apply filters if provided
    if first_name:
        query = query.filter(models.Employee.first_name.ilike(f'%{first_name}%'))
    if last_name:
        query = query.filter(models.Employee.last_name.ilike(f'%{last_name}%'))
    if email:
        query = query.filter(models.Employee.email.ilike(f'%{email}%'))
    if date_of_joining:
        # user_date = str(datetime.strptime(date_of_joining, '%Y-%m-%d').date())
        # query = query.filter(models.Employee.date_of_joining == user_date)
        user_date = datetime.strptime(date_of_joining, '%Y-%m-%d')
        start_of_day = datetime(user_date.year, user_date.month, user_date.day, 0, 0, 0)
        end_of_day = datetime(user_date.year, user_date.month, user_date.day, 23, 59, 59)
        query = query.filter(models.Employee.date_of_joining >= start_of_day,
                             models.Employee.date_of_joining <= end_of_day)

    # Sort by email in ascending order
    query = query.order_by(asc(models.Employee.email))
    employees = query.all()
    if not employees:
        raise HTTPException(status_code=400,
                            detail=f"Employees could not found with this parameters")

    # admin can see all details and user only selected
    if current_user.role == "ADMIN":
        return employees
    else:
        return [schemas.ShowEmployee.from_orm(employee) for employee in employees]


@app.get('/employees/{email}')
async def get_employee(email: str, db: Session = Depends(get_db),
                       current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    email = email.lower()
    await check_for_activation(current_user)
    employee = db.query(models.Employee).filter(models.Employee.email == email).first()
    if not employee:
        raise HTTPException(status_code=400,
                            detail=f"Employee with this {email} could not be found")
    # admin can see all details and user only selected
    if current_user.role == "ADMIN":
        return employee
    else:
        return schemas.ShowEmployee.from_orm(employee)


@app.put('/employees/{email}')
async def update_employee(email: str, request: schemas.UpdateEmployee, db: Session = Depends(get_db),
                          current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    email = email.lower()
    await check_for_activation(current_user)
    if current_user.role == "ADMIN":
        employee = db.query(models.Employee).filter(models.Employee.email == email)
        if not employee.first():
            raise HTTPException(status_code=400,
                                detail=f"Employee with this {email} could not be found")
        db_request = request.dict()
        db_request["updated_at"] = datetime.utcnow()
        db_request["updated_by"] = employee.first().id
        employee.update(db_request)
        db.commit()
        return {"status": "employee updated successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"You dont have sufficient privileges")


@app.delete('/employees/{email}')
async def delete_employee(email: str, db: Session = Depends(get_db),
                          current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    await check_for_activation(current_user)
    email = email.lower()
    if current_user.role == "ADMIN":
        employee = db.query(models.Employee).filter(models.Employee.email == email)
        if not employee.first():
            raise HTTPException(status_code=400,
                                detail=f"Employee with this {email} could not be found")
        employee.delete(synchronize_session=False)
        db.commit()
        return {"status": "employee deleted successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"You dont have sufficient privileges")


@app.post('/reset-password')
async def reset_password(request: schemas.ResetPassword, db: Session = Depends(get_db),
                         current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    await check_for_activation(current_user)
    user = db.query(models.Employee).filter(models.Employee.email == current_user.email)
    db_user = user.first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Invalid Credentials")
    if not hashing.Hash.verify(db_user.password, request.current_password):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incorrect password")
    try:
        dummy = schemas.PasswordValidate(new_password=request.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    user.update({"password": hashing.Hash.bcrypt(request.new_password)})
    db.commit()
    return {"status": "password reset successful"}


@app.post('/reset-password-admin/{email}')
async def reset_password_admin(email: str, db: Session = Depends(get_db),
                               current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    email = email.lower()
    await check_for_activation(current_user)
    if current_user.role == "ADMIN":
        user = db.query(models.Employee).filter(models.Employee.email == email)
        db_user = user.first()
        if not db_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Invalid Credentials")
        user.update({"password": hashing.Hash.bcrypt("Test@12345")})
        db.commit()
        return {"status": f"password reset for {email} successful"}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"You dont have sufficient privileges")


async def check_for_activation(current_user):
    if not current_user.is_active:
        raise HTTPException(status_code=400,
                            detail="Please activate your account by updating your password through "
                                   "/update-password-first-time url then you will have all functionality")


if __name__ == '__main__':
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
