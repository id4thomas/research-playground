from pydantic import BaseModel


class ApiRequest[T](BaseModel):
    data: T
