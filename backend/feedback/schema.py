from pydantic import BaseModel
from typing import Optional, Dict, Any

class AnswerFeedback(BaseModel):
    answer_id: str
    rating: Optional[int] = None
    helpful: Optional[bool] = None
    flags: Optional[Dict[str, Any]] = None
    comments: Optional[str] = None

class ModuleFeedback(BaseModel):
    module_id: str
    rating: Optional[int] = None
    helpful: Optional[bool] = None
    flags: Optional[Dict[str, Any]] = None
    comments: Optional[str] = None
