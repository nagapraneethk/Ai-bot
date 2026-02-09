"""
Chat API endpoint with smart LLM-based routing.
Uses LLM to decide whether to scrape or use knowledge.
Falls back to aggregator sites (Shiksha, Collegedunia) for rich data.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import College, CollegePage
from app.schemas import ChatRequest, ChatResponse
from app.services.llm import answer_question, detect_intent, classify_question, answer_with_llm_knowledge
from app.services.dynamic_scraper import scrape_for_intent, scrape_from_aggregators
from app.services.groq_service import classify_question_groq, answer_question_groq, answer_with_knowledge_groq
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/chat", tags=["chat"])


def has_specific_data(content: str, intent: str) -> bool:
    """Check if content has actual specific data (numbers, stats) for the intent."""
    if intent == "placements":
        # Check for salary/package numbers (LPA, lakhs, crore, etc.)
        import re
        has_numbers = bool(re.search(r'\d+\.?\d*\s*(lpa|lakhs?|crore?|cr|lakh|%)', content.lower()))
        return has_numbers
    elif intent == "fees":
        # Check for fee amounts
        import re
        has_fees = bool(re.search(r'(₹|rs\.?|inr)\s*\d+|(\d+,?\d*)\s*(per|/)\s*(year|annum|semester)', content.lower()))
        return has_fees
    return True  # For other intents, assume content is sufficient


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Answer a question about a college.
    Strategy:
    1. LLM classifies question (needs scrape or knowledge?)
    2. Try official website first
    3. If no specific data found, try aggregators (Shiksha, Collegedunia)
    4. Final fallback: LLM knowledge
    """
    if not request.question or len(request.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="Question must be at least 3 characters")
    
    # Get college
    result = await db.execute(
        select(College).where(College.id == request.college_id)
    )
    college = result.scalar_one_or_none()
    
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    if not college.scraped:
        raise HTTPException(
            status_code=400, 
            detail="College data has not been scraped yet. Please confirm the college first."
        )
    
    question = request.question.strip()
    
    
    # Use LLM to classify the question
    if settings.use_groq and settings.groq_api_key:
        print(f"[AI] Using Groq for classification")
        needs_scrape, intent = await classify_question_groq(question)
    else:
        needs_scrape, intent = await classify_question(question)
    
    print(f"[AI] Question classification: needs_scrape={needs_scrape}, intent={intent}")

    # Force scrape if intent is specific (placements, fees, etc.) to ensure fresh data
    if intent in ["placements", "fees", "admissions", "facilities", "about"] and not needs_scrape:
        print(f"[FORCE] Forcing scrape for specific intent: {intent}")
        needs_scrape = True
    
    # If LLM says we don't need to scrape, use its knowledge directly
    if not needs_scrape:
        print(f"[KNOWLEDGE] Using LLM knowledge for: {question}")
        if settings.use_groq and settings.groq_api_key:
            answer = await answer_with_knowledge_groq(question, college.college_name)
        else:
            answer = await answer_with_llm_knowledge(question, college.college_name)
        main_url = f"https://{college.official_domain}" if college.official_domain else None
        return ChatResponse(answer=answer, source_page="LLM knowledge", source_url=main_url)
    
    # Check cached content
    pages_result = await db.execute(
        select(CollegePage).where(CollegePage.college_id == request.college_id)
    )
    pages = pages_result.scalars().all()
    
    pages_data = [
        {
            "page_type": page.page_type,
            "content_text": page.content_text,
            "source_url": page.source_url
        }
        for page in pages
    ]
    
    existing_types = {p["page_type"] for p in pages_data}
    
    # Check if we have good data for this intent
    intent_content = next((p["content_text"] for p in pages_data if p["page_type"] == intent), "")
    has_good_data = has_specific_data(intent_content, intent) if intent_content else False
    
    # Try to scrape if we don't have good content OR user wants dynamic scraping (now default)
    if intent not in existing_types or not has_good_data or True: # Force check for specific page
        print(f"[SCRAPE] Dynamic scrape trigger for: {intent}")
        
        base_url = f"https://{college.official_domain}"
        
        # ALWAYS try official website first
        try:
            new_page_data = await scrape_for_intent(base_url, intent)
            if new_page_data:
                content = new_page_data.get("content_text", "")
                new_page = CollegePage(
                    college_id=college.id,
                    page_type=new_page_data["page_type"],
                    content_text=content,
                    source_url=new_page_data["source_url"]
                )
                db.add(new_page)
                await db.commit()
                pages_data.append(new_page_data)
                print(f"[SUCCESS] Cached {intent} page from official site")
        except Exception as e:
            print(f"[ERROR] Official scrape failed: {e}")

        # ALWAYS try aggregators too (for richer context)
        try:
            print(f"[SEARCH] Fetching third-party data from aggregators for {intent}...")
            agg_data = await scrape_from_aggregators(college.college_name, intent)
            if agg_data:
                 new_page = CollegePage(
                    college_id=college.id,
                    page_type=agg_data["page_type"] + "_aggregator", # Distinguish type
                    content_text=agg_data["content_text"],
                    source_url=agg_data["source_url"]
                )
                 db.add(new_page)
                 await db.commit()
                 pages_data.append(agg_data)
                 print(f"[SUCCESS] Cached {intent} data from aggregator (Shiksha/Collegedunia)")
        except Exception as e:
            print(f"[ERROR] Aggregator scrape failed: {e}")
    
    # If no scraped data, fall back to LLM knowledge
    if not pages_data:
        print(f"[FALLBACK] No scraped data, using LLM knowledge as fallback")
        if settings.use_groq and settings.groq_api_key:
            answer = await answer_with_knowledge_groq(question, college.college_name)
        else:
            answer = await answer_with_llm_knowledge(question, college.college_name)
        main_url = f"https://{college.official_domain}" if college.official_domain else None
        return ChatResponse(answer=answer, source_page="LLM knowledge", source_url=main_url)
    
    # Answer using scraped content
    if settings.use_groq and settings.groq_api_key:
        print(f"[AI] Using Groq for answer generation")
        # Reuse get_relevant_content from llm module as it's just logic
        from app.services.llm import get_relevant_content, detect_intent
        
        intents = detect_intent(question)
        print(f"[DETECT] Groq detected intents: {intents}")
        content, source_page, source_url, sources = get_relevant_content(pages_data, intents)
        print(f"[CONTENT] Groq relevant content length: {len(content) if content else 0} chars from {source_page}")
        if content:
            print(f"DEBUG CONTENT EXCERPT (first 500 chars): {content[:500]}")
        
        if not content.strip():
            answer = f"I don't have enough information about {college.college_name} to answer this question."
        else:
            answer = await answer_question_groq(question, content, college.college_name)
            
        return ChatResponse(answer=answer, source_page=source_page, source_url=source_url or "", sources=sources)
    else:
        answer, source_page, source_url, sources = await answer_question(
            question=question,
            pages=pages_data,
            college_name=college.college_name
        )
    
    return ChatResponse(answer=answer, source_page=source_page, source_url=source_url, sources=sources)
