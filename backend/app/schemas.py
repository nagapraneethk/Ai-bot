from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime


# College Resolution
class CollegeResolveRequest(BaseModel):
    college_name: str
    force_search: bool = False  # If True, skip known colleges and search the web


class CollegeCandidate(BaseModel):
    name: str
    url: str
    confidence: str  # high, medium, low


class CollegeResolveResponse(BaseModel):
    candidates: List[CollegeCandidate]


# College Confirmation
class CollegeConfirmRequest(BaseModel):
    url: str
    college_name: str


class CollegeConfirmResponse(BaseModel):
    college_id: int
    status: str  # scraped, already_exists, scraping_failed
    pages_count: int
    message: Optional[str] = None


# Chat
class ChatRequest(BaseModel):
    college_id: int
    question: str


class ChatResponse(BaseModel):
    answer: str
    source_page: Optional[str] = None
    source_url: Optional[str] = None
    sources: List[dict] = []  # List of {type: str, url: str}


# College Info
class CollegeInfo(BaseModel):
    id: int
    college_name: str
    official_domain: str
    scraped: bool
    pages_count: int
    created_at: datetime

    class Config:
        from_attributes = True
