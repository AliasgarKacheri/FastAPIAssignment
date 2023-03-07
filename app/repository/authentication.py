from fastapi import HTTPException, status
from sqlalchemy.orm import Session, Query
from app import schemas
from app.security import JWTtoken
from app.security import hashing
from app.database import models

from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime
from app.utility import check_for_activation
from app.logger import logger
from app.utility import DEFAULT_PASSWORD


async def login(request: OAuth2PasswordRequestForm, db: Session):
    logger.debug("inside login method")
    user_db = db.query(models.Employee).filter(models.Employee.email == request.username)
    user = user_db.first()
    if not user:
        logger.error(f"invalid credentials")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Invalid Credentials")
    if not hashing.Hash.verify(user.password, request.password):
        logger.error(f"incorrect password of user {user.email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"Incorrect password")
    if not user.is_active:
        logger.error(f'user is not active {user.email}')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"Please update your password by going to this "
                                   f"link localhost/update-password-first-time")
    access_token = JWTtoken.create_access_token(
        data={"sub": user.email, "role": user.role.name, "is_active": user.is_active, "id": user.id})
    # update last_login
    user_db.update({"last_login": datetime.utcnow()})
    db.commit()
    logger.debug(f"successfully logged in user {user.email}")
    return {"access_token": access_token, "token_type": "Bearer"}


async def update_password(request: schemas.LoginUser, db: Session):
    logger.debug("inside update_password method")
    user = db.query(models.Employee).filter(models.Employee.email == request.email)
    db_user = user.first()
    if not db_user:
        logger.error(f"invalid credentials")
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
        logger.debug(f"successfully updated password for user {db_user.email}")
        return {"status": "successfully updated password now you can login"}
    else:
        logger.error(f"user not active {db_user.email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Only First time login can update the password")


async def reset_password(request: schemas.ResetPassword, db: Session,
                         current_user: schemas.TokenData):
    logger.debug("inside reset_password method")
    await check_for_activation(current_user)
    user = db.query(models.Employee).filter(models.Employee.email == current_user.email)
    db_user = user.first()
    if not db_user:
        logger.error(f"invalid credentials")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Invalid Credentials")
    if not hashing.Hash.verify(db_user.password, request.current_password):
        logger.error(f"incorrect password of user {db_user.email}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incorrect password")
    try:
        dummy = schemas.PasswordValidate(new_password=request.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    user.update({"password": hashing.Hash.bcrypt(request.new_password)})
    db.commit()
    logger.debug(f"successful reset password for user {db_user.email}")
    return {"status": "password reset successful"}


async def reset_password_admin(email: str, db: Session,
                               current_user: schemas.TokenData):
    logger.debug("inside reset_password_admin method")
    email = email.lower()
    await check_for_activation(current_user)
    if current_user.role == "ADMIN":
        user = db.query(models.Employee).filter(models.Employee.email == email)
        db_user = user.first()
        if not db_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Invalid Credentials")
        user.update({"password": hashing.Hash.bcrypt(DEFAULT_PASSWORD), "is_active": False})
        db.commit()
        logger.debug(f"successfully reset password by admin for user {db_user.email}")
        return {"status": f"password reset for {email} successful"}
    else:
        logger.error(f"insufficient privileges for user with email {current_user.email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"You dont have sufficient privileges")
