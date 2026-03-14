from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


# --- Request schemas ---

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# --- Response schemas ---

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Token schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None