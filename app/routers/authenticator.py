from fastapi import Depends, APIRouter, status
from sqlalchemy.orm import Session
from app import schemas
from app.database.database import get_db
from app.security import oauth2
from fastapi.security import OAuth2PasswordRequestForm
from app.repository import authentication

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post('/login', status_code=status.HTTP_200_OK)
async def login(request: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return await authentication.login(request, db)


@router.post('/update-password-first-time', status_code=status.HTTP_200_OK)
async def update_password(request: schemas.LoginUser, db: Session = Depends(get_db)):
    return await authentication.update_password(request, db)


@router.post('/reset-password', status_code=status.HTTP_200_OK)
async def reset_password(request: schemas.ResetPassword, db: Session = Depends(get_db),
                         current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    return await authentication.reset_password(request, db, current_user)


@router.post('/reset-password-admin/{email}', status_code=status.HTTP_200_OK)
async def reset_password_admin(email: str, db: Session = Depends(get_db),
                               current_user: schemas.TokenData = Depends(oauth2.get_current_user)):
    return await authentication.reset_password_admin(email, db, current_user)
