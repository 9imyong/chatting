from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    trace_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
