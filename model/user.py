from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

def ResponseModel(data, message):
    return {
        "data": data,
        "code": 200,
        "message": message,
    }

class User(BaseModel):
    identity_id: str
    birth_date: str
    full_name: str
    disabled: bool = False
    evaluate_datetime: Optional[datetime] = None
    create_datetime: Optional[datetime] = None


class UserInDB(User):
    hashed_password: str


class UserRole(str, Enum):
    boss = "boss"
    employee = "employee"