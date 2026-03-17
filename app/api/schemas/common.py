from pydantic import BaseModel


class ApiErrorResponse(BaseModel):
    status: str = "error"
    message: str
    request_id: str
    trace_id: str
    error_code: str
