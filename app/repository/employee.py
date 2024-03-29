import csv
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import schemas
from security import hashing
from database import models
import codecs
from utility import check_for_activation, check_date_is_iso
from datetime import datetime
from utility import DEFAULT_PASSWORD
from logger import logger


def bulk_upload_employees(file: UploadFile, db: Session):
    logger.debug("inside bulk_upload_employees method")

    # Check file name
    if file.filename != "bulk_upload_employees.csv":
        logger.error(f"file name is incorrect {file.filename}")
        raise HTTPException(status_code=400, detail="Invalid file name")

    # Check file format
    file_format = file.filename.split(".")[-1]
    if file_format not in ["csv", "xls", 'vnd.ms-excel']:
        logger.error(f"file format is incorrect {file.filename}")
        raise HTTPException(status_code=400, detail="Invalid file format")

    # Process CSV file
    try:
        csv_data = csv.DictReader(codecs.iterdecode(file.file, 'utf-8'))
    except Exception as e:
        logger.error("invalid file content")
        raise HTTPException(status_code=400, detail=f"Invalid file content: {e}")

    employees_added = 0
    employees_ignored = 0
    # check if fields names are same as we want
    field_names = {"first_name", "last_name", "yrs_of_experience", "role", "email"}
    if len(csv_data.fieldnames) == len(field_names):
        for field in csv_data.fieldnames:
            if field not in field_names:
                logger.error("invalid file header")
                raise HTTPException(status_code=400, detail=f"Invalid file header")
    for row in csv_data:
        try:
            employee_data = schemas.Employee(**row)
        except ValueError as e:
            logger.error(f"Value error for employee {row['email']}, {str(e)}")
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
            logger.debug(f"successfully added employee with email {db_employee.email}")
        except IntegrityError as e:
            employees_ignored += 1
            db.rollback()
            continue
        employees_added += 1
    return {"status": f"uploaded: employees added {employees_added}, employee ignored {employees_ignored}"}


async def all_employees(first_name, last_name, email, date_of_joining, db: Session,
                        current_user: schemas.TokenData):
    logger.debug("inside all_employees method")
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
        # validate date
        check_date_is_iso(date_of_joining)
        user_date = str(datetime.strptime(date_of_joining, '%Y-%m-%d').date())
        query = query.filter(models.Employee.date_of_joining == user_date)

    # Sort by email in ascending order
    query = query.order_by(asc(models.Employee.email))
    employees = query.all()
    if not employees:
        logger.error("No employees found for given filters")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Employees could not found with this parameters")

    # admin can see all details and user only selected
    if current_user.role == "ADMIN":
        return employees
    else:
        return [schemas.ShowEmployee.from_orm(employee) for employee in employees]


async def get_employee(email: str, db: Session, current_user: schemas.TokenData):
    logger.debug("inside get_employee method")
    email = email.lower()
    await check_for_activation(current_user)
    employee = db.query(models.Employee).filter(models.Employee.email == email).first()
    if not employee:
        logger.error(f"No employee found with given email {email}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Employee with this {email} could not be found")
    # admin can see all details and user only selected
    if current_user.role == "ADMIN":
        return employee
    else:
        return schemas.ShowEmployee.from_orm(employee)


async def update_employee(email: str, request: schemas.UpdateEmployee, db: Session,
                          current_user: schemas.TokenData):
    logger.debug("inside update_employee method")
    email = email.lower()
    await check_for_activation(current_user)
    if current_user.role == "ADMIN":
        employee = db.query(models.Employee).filter(models.Employee.email == email)
        if not employee.first():
            logger.error(f"No employee found with given email {email}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Employee with this {email} could not be found")
        db_request = request.dict()
        db_request["updated_at"] = datetime.utcnow()
        db_request["updated_by"] = current_user.id
        employee.update(db_request)
        db.commit()
        logger.debug(f"employee updated successfully with email {email}")
        return {"status": "employee updated successfully"}
    else:
        logger.error(f"insufficient privileges for user with email {current_user.email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"You dont have sufficient privileges")


async def delete_employee(email: str, db: Session, current_user: schemas.TokenData):
    logger.debug("inside delete_employee method")
    await check_for_activation(current_user)
    email = email.lower()
    if current_user.role == "ADMIN":
        employee = db.query(models.Employee).filter(models.Employee.email == email)
        if not employee.first():
            logger.error(f"No employee found with given email {email}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Employee with this {email} could not be found")
        employee.delete(synchronize_session=False)
        db.commit()
        logger.debug(f"employee deleted successfully with email {email}")
        return {"status": "employee deleted successfully"}
    else:
        logger.error(f"insufficient privileges for user with email {current_user.email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"You dont have sufficient privileges")
