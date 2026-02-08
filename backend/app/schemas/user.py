from pydantic import BaseModel
from typing import Optional


class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class UpdateUserRequest(BaseModel):
    is_admin: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool

    model_config = {"from_attributes": True}
