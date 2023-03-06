import csv
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app import schemas
from app.security import hashing
from app.database import models
import codecs
from app.utility import check_for_activation
from datetime import datetime

DEFAULT_PASSWORD = "Test@12345"


def bulk_upload_employees(file: UploadFile, db: Session):
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


async def all_employees(first_name, last_name, email, date_of_joining, db: Session,
                        current_user: schemas.TokenData):
    await check_for_activation(current_user)
    # Query the database for all employees
    query = db.query(models.Employee)

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


async def get_employee(email: str, db: Session, current_user: schemas.TokenData):
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


async def update_employee(email: str, request: schemas.UpdateEmployee, db: Session,
                          current_user: schemas.TokenData):
    email = email.lower()
    await check_for_activation(current_user)
    if current_user.role == "ADMIN":
        employee = db.query(models.Employee).filter(models.Employee.email == email)
        if not employee.first():
            raise HTTPException(status_code=400,
                                detail=f"Employee with this {email} could not be found")
        db_request = request.dict()
        db_request["updated_at"] = datetime.utcnow()
        db_request["updated_by"] = current_user.id
        employee.update(db_request)
        db.commit()
        return {"status": "employee updated successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"You dont have sufficient privileges")


async def delete_employee(email: str, db: Session, current_user: schemas.TokenData):
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
