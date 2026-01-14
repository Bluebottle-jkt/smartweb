from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.security import verify_password, create_access_token
from app.db.session import get_db
from app.db.models.user import UserAccount
from app.api.deps import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True


@router.post("/login")
def login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Login and set httpOnly cookie with JWT token."""
    user = db.query(UserAccount).filter(UserAccount.username == login_data.username).first()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": user.username})

    # Set httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=60 * 60 * 24,  # 24 hours
        samesite="lax"
    )

    return {"message": "Login successful", "user": UserResponse.from_orm(user)}


@router.post("/logout")
def logout(response: Response):
    """Logout by clearing the cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: UserAccount = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserResponse.from_orm(current_user)
