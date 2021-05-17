from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, Field
from enum import Enum

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    identity_id: Optional[str] = None