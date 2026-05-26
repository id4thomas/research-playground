from typing import Optional

from pydantic import BaseModel


class ApiResponse[T](BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None
