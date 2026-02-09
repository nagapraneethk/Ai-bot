"""
College-related API endpoints.
Handles college resolution, confirmation, and dynamic scraping.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import College, CollegePage
from app.schemas import (
    CollegeResolveRequest, 
    CollegeResolveResponse, 
    CollegeCandidate,
    CollegeConfirmRequest, 
    CollegeConfirmResponse,
    CollegeInfo
)
from app.services.search import search_college_website
from app.services.dynamic_scraper import quick_scrape_homepage

router = APIRouter(prefix="/college", tags=["college"])


@router.post("/resolve", response_model=CollegeResolveResponse)
async def resolve_college(request: CollegeResolveRequest):
    """
    Search for official college websites based on college name.
    Returns candidate websites for user confirmation.
    
    If force_search is True, skip the known colleges database and search the web.
    """
    if not request.college_name or len(request.college_name.strip()) < 3:
        raise HTTPException(status_code=400, detail="College name must be at least 3 characters")
    
    candidates = search_college_website(
        request.college_name.strip(), 
        force_web_search=request.force_search
    )
    
    if not candidates:
        raise HTTPException(
            status_code=404, 
            detail="Could not find any official website for this college. Please try with a different name or spelling."
        )
    
    return CollegeResolveResponse(
        candidates=[CollegeCandidate(**c) for c in candidates]
    )


@router.post("/confirm", response_model=CollegeConfirmResponse)
async def confirm_college(
    request: CollegeConfirmRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm a college website and trigger scraping if needed.
    Returns college ID for subsequent chat requests.
    """
    from urllib.parse import urlparse
    
    # Parse and validate URL
    try:
        parsed = urlparse(request.url)
        domain = parsed.netloc.lower()
        if not domain:
            raise ValueError("Invalid URL")
    except:
        raise HTTPException(status_code=400, detail="Invalid URL provided")
    
    # Check if college already exists
    result = await db.execute(
        select(College).where(College.official_domain == domain)
    )
    existing_college = result.scalar_one_or_none()
    
    if existing_college and existing_college.scraped:
        # Get page count
        pages_result = await db.execute(
            select(CollegePage).where(CollegePage.college_id == existing_college.id)
        )
        pages = pages_result.scalars().all()
        
        return CollegeConfirmResponse(
            college_id=existing_college.id,
            status="already_exists",
            pages_count=len(pages),
            message=f"College data already available with {len(pages)} pages scraped."
        )
    
    # Create or update college record
    if existing_college:
        college = existing_college
    else:
        college = College(
            college_name=request.college_name.strip(),
            official_domain=domain,
            scraped=False
        )
        db.add(college)
        await db.flush()  # Get the ID
    
    # Quick scrape - just homepage for initial setup (fast!)
    try:
        homepage_data = await quick_scrape_homepage(request.url)
    except Exception as e:
        print(f"Scraping error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to access website: {str(e)}"
        )
    
    if not homepage_data:
        # Still mark as ready - we'll do dynamic scraping on questions
        college.scraped = True
        await db.commit()
        
        return CollegeConfirmResponse(
            college_id=college.id,
            status="ready",
            pages_count=0,
            message="College confirmed! Content will be fetched dynamically when you ask questions."
        )
    
    # Store homepage content
    page = CollegePage(
        college_id=college.id,
        page_type=homepage_data["page_type"],
        content_text=homepage_data["content_text"],
        source_url=homepage_data["source_url"]
    )
    db.add(page)
    
    # Mark college as ready
    college.scraped = True
    
    await db.commit()
    
    return CollegeConfirmResponse(
        college_id=college.id,
        status="ready",
        pages_count=1,
        message="College confirmed! Additional content will be fetched when you ask questions."
    )


@router.get("/{college_id}", response_model=CollegeInfo)
async def get_college(college_id: int, db: AsyncSession = Depends(get_db)):
    """Get college information by ID."""
    result = await db.execute(
        select(College).where(College.id == college_id)
    )
    college = result.scalar_one_or_none()
    
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    # Get page count
    pages_result = await db.execute(
        select(CollegePage).where(CollegePage.college_id == college_id)
    )
    pages = pages_result.scalars().all()
    
    return CollegeInfo(
        id=college.id,
        college_name=college.college_name,
        official_domain=college.official_domain,
        scraped=college.scraped,
        pages_count=len(pages),
        created_at=college.created_at
    )
