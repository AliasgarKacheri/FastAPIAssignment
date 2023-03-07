from fastapi import HTTPException
from app.logger import logger

DEFAULT_PASSWORD = "Test@12345"


async def check_for_activation(current_user):
    if not current_user.is_active:
        logger.error(f"Giver user is not active {current_user.email}")
        raise HTTPException(status_code=400,
                            detail="Please activate your account by updating your password through "
                                   "/update-password-first-time url then you will have all functionality")
