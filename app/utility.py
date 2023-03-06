from fastapi import HTTPException


async def check_for_activation(current_user):
    if not current_user.is_active:
        raise HTTPException(status_code=400,
                            detail="Please activate your account by updating your password through "
                                   "/update-password-first-time url then you will have all functionality")
