
from typing import Optional
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """Standard API response model"""
    status: str
    message: str
    data: Optional[dict] = None

class ErrorResponse(BaseModel):
    """Standard error response model"""
    status: str = "error"
    error: dict
