import csv
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import schemas
from security import JWTtoken
from database import Base, engine, get_db
import models
import uvicorn
import codecs
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime

app = FastAPI()
Base.metadata.create_all(engine)


@app.get('/')
async def root():
    return {'message': 'Hello World!'}


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
        # created_by = Column(String(50))
        # updated_by = Column(String(50))
        db_employee = employee_data.dict()
        db_employee["role_id"] = 1 if row["role"] == "USER" else 2
        db_employee["created_by"] = 1
        db_employee["updated_by"] = 1
        del db_employee["role"]
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
    user = db.query(models.Employee).filter(models.Employee.email == request.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Invalid Credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Please update your password by going to this link localhost/update-password")
    # if not Hash().verify(user.password, request.password):
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
    #                         detail=f"Incorrect password")
    if not user.password == request.password:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Incorrect password")
    role = "USER" if user.role_id == 1 else "ADMIN"
    access_token = JWTtoken.create_access_token(data={"sub": user.email, "role": role})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post('/update-password')
def login(request: schemas.LoginUser, db: Session = Depends(get_db)):
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
        user.update(request_dict)
        db.commit()
        return {"status": "successfully updated password now you can login"}
    else:
        raise HTTPException(status_code=400, detail="Only First time login can change the password")



if __name__ == '__main__':
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
