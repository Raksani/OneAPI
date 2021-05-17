from typing import Optional

from pydantic import BaseModel, EmailStr, Field

def ResponseModel(data, message):
    return {
        "data": data,
        "code": 200,
        "message": message,
    }