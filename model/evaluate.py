from typing import List, Optional
from datetime import datetime
from fastapi.openapi.models import Example
from pydantic import BaseModel
from enum import Enum

from pydantic.fields import Field


class Evaluate(BaseModel):
    evaluate_list: List = Field(..., example=[
        {
            'identity_id': "E4933029966394",
            'score': 4.5
        },
        {
            'identity_id': "E4933029966394",
            'score': 2
        },
    ])


