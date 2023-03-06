from fastapi import HTTPException, status
from sqlalchemy.orm import Session, Query
from app import schemas
from app.security import JWTtoken
from app.security import hashing
from app.database import models

from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime
from app.utility import check_for_activation


async def login(request: OAuth2PasswordRequestForm, db: Session):
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
                            detail=f"Please update your password by going to this "
                                   f"link localhost/update-password-first-time")
    access_token = JWTtoken.create_access_token(
        data={"sub": user.email, "role": user.role.name, "is_active": user.is_active, "id": user.id})
    # update last_login
    user_db.update({"last_login": datetime.utcnow()})
    db.commit()
    return {"access_token": access_token, "token_type": "Bearer"}


async def update_password(request: schemas.LoginUser, db: Session):
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


async def reset_password(request: schemas.ResetPassword, db: Session,
                         current_user: schemas.TokenData):
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


async def reset_password_admin(email: str, db: Session,
                               current_user: schemas.TokenData):
    email = email.lower()
    await check_for_activation(current_user)
    if current_user.role == "ADMIN":
        user = user = db.query(models.Employee).filter(models.Employee.email == email)
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
