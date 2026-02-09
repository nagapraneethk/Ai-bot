"""
LLM service using Google Gemini for question answering.
Uses RAG-style prompting with scraped content.
"""

import google.generativeai as genai
from typing import List, Dict, Optional, Tuple
from app.config import get_settings

settings = get_settings()

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

# Use Gemini 2.5 Flash model (free tier compatible)
model = genai.GenerativeModel("gemini-2.5-flash")


# Intent keywords for routing to correct content
INTENT_KEYWORDS = {
    "fees": ["fee", "fees", "cost", "tuition", "payment", "scholarship", "price", "afford", "expense", "charges"],
    "admissions": ["admission", "apply", "eligibility", "entrance", "cutoff", "requirement", "enroll", "registration", "intake"],
    "placements": ["placement", "salary", "package", "recruit", "company", "job", "career", "intern", "average package", "highest package"],
    "academics": ["course", "program", "degree", "curriculum", "subject", "faculty", "professor", "department", "branch", "specialization"],
    "about": ["history", "established", "founder", "accreditation", "ranking", "recognition", "about", "overview"],
    "facilities": ["hostel", "library", "lab", "campus", "infrastructure", "facility", "amenity", "sports", "canteen"],
    "contact": ["contact", "address", "location", "phone", "email", "reach", "where"],
}


def detect_intent(question: str) -> List[str]:
    """
    Detect the intent/topic of a question.
    Returns list of relevant page types.
    """
    question_lower = question.lower()
    intents = []
    
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in question_lower for keyword in keywords):
            intents.append(intent)
    
    # If no specific intent, return general
    if not intents:
        intents = ["about", "general"]
    
    return intents


async def classify_question(question: str) -> Tuple[bool, str]:
    """
    Use LLM to classify whether a question needs fresh website data or general knowledge.
    
    Returns:
        Tuple of (needs_scrape: bool, intent: str)
        - needs_scrape: True if we need to scrape website for current data
        - intent: The type of information needed (placements, fees, admissions, about, general)
    """
    prompt = f"""Classify this question about a college.

QUESTION: "{question}"

Determine:
1. Does this question need CURRENT/SPECIFIC data from the college website? (placement stats, fee amounts, admission cutoffs, current faculty)
2. Or can it be answered from GENERAL KNOWLEDGE? (history, founding year, location, rankings, famous alumni, what the college is known for)

Respond in EXACTLY this format (one line only):
SCRAPE:<yes/no>|INTENT:<placements/fees/admissions/about/general>

Examples:
- "What is the highest package?" → SCRAPE:yes|INTENT:placements
- "When was this college founded?" → SCRAPE:no|INTENT:about  
- "What is the fee structure?" → SCRAPE:yes|INTENT:fees
- "Who is the director?" → SCRAPE:no|INTENT:about
- "What is this college known for?" → SCRAPE:no|INTENT:general
- "What is the admission cutoff?" → SCRAPE:yes|INTENT:admissions

Your response (one line only):"""

    try:
        response = model.generate_content(prompt)
        result = response.text.strip().upper()
        
        # Parse response
        if "SCRAPE:" in result and "INTENT:" in result:
            parts = result.split("|")
            scrape_part = parts[0].replace("SCRAPE:", "").strip()
            intent_part = parts[1].replace("INTENT:", "").strip().lower()
            
            needs_scrape = scrape_part == "YES"
            intent = intent_part if intent_part in ["placements", "fees", "admissions", "about", "general"] else "general"
            
            return needs_scrape, intent
        
        # Fallback to keyword detection if LLM response is malformed
        intents = detect_intent(question)
        needs_scrape = any(i in ["placements", "fees", "admissions"] for i in intents)
        return needs_scrape, intents[0] if intents else "general"
        
    except Exception as e:
        print(f"Classification error: {e}")
        # Fallback to keyword-based detection
        intents = detect_intent(question)
        needs_scrape = any(i in ["placements", "fees", "admissions"] for i in intents)
        return needs_scrape, intents[0] if intents else "general"


def get_relevant_content(pages: List[Dict], intents: List[str], max_tokens: int = 8000) -> Tuple[str, str, Optional[str], List[Dict[str, str]]]:
    """
    Get relevant content based on detected intents.
    Returns tuple of (content, primary_source_page_type, primary_source_url, all_sources)
    """
    relevant_pages = []
    
    # First, add pages matching intents (official and aggregator)
    for intent in intents:
        for page in pages:
            # Match strict intent or intent_aggregator
            if (page["page_type"] == intent or page["page_type"] == f"{intent}_aggregator") and page not in relevant_pages:
                relevant_pages.append(page)
    
    # Then add general pages if needed
    for page in pages:
        if page["page_type"] == "general" and page not in relevant_pages:
            relevant_pages.append(page)
    
    # If still not enough content, keep adding other types to ensure we pass something
    if len(relevant_pages) == 0 and len(pages) > 0:
        relevant_pages.extend(pages) # Fallback to everything we have if strict matching fails
    
    # Build content string
    content_parts = []
    total_chars = 0
    char_limit = max_tokens * 4  # Rough char to token ratio
    primary_source_type = None
    primary_source_url = None
    all_sources = []
    
    for page in relevant_pages:
        page_content = page["content_text"]
        
        if total_chars + len(page_content) > char_limit:
            remaining = char_limit - total_chars
            if remaining > 500:
                page_content = page_content[:remaining]
            else:
                break
                
        content_parts.append(f"--- {page['page_type'].upper()} PAGE ---\n{page_content}")
        total_chars += len(page_content)
        
        if primary_source_type is None:
            primary_source_type = page["page_type"]
            primary_source_url = page.get("source_url")
        
        if page.get("source_url"):
            all_sources.append({
                "type": page["page_type"],
                "url": page["source_url"]
            })
    
    return "\n\n".join(content_parts), primary_source_type or "general", primary_source_url, all_sources


async def answer_question(question: str, pages: List[Dict], college_name: str) -> Tuple[str, Optional[str], Optional[str], List[Dict[str, str]]]:
    """
    Answer a question using the scraped content.
    Returns: Tuple of (answer, source_page_type, source_url, sources_list)
    """
    if not pages:
        return "I don't have any information about this college yet. Please wait while the data is being scraped.", None, None, []
    
    # Detect intent
    intents = detect_intent(question)
    
    # Get relevant content
    content, source_page, source_url, sources = get_relevant_content(pages, intents)
    
    if not content.strip():
        return f"I don't have enough information about {college_name} to answer this question.", None, None, []
    
    # Build prompt with strict guardrails
    prompt = f"""You are a college information assistant ONLY for {college_name}.

CONTEXT FROM OFFICIAL WEBSITE:
{content}

RULES:
1. ONLY answer questions about {college_name}
2. If the user asks about ANY other topic, politely say: "I can only answer questions about {college_name}."
3. IMPORTANT: If the website content above does NOT contain the specific data asked (like exact package numbers, percentages, etc.):
   - Use your built-in knowledge about {college_name} if you have reliable information
   - Mention that you're providing data from your knowledge and it may not be the latest
   - Example: "Based on available data, IIT Bombay's highest package was around 2.3 Cr (as of 2023-24). For the latest 2025 figures, please check the official placement portal."
4. If you provide numbers from your knowledge, always add a note that users should verify with the official website for latest data
5. Be helpful and informative - don't just say "not available" if you know the answer
6. Do NOT make up numbers you don't know
7. Do NOT use emojis in your response.

USER QUESTION: {question}

Provide a helpful answer using both the website content and your knowledge:"""

    try:
        response = model.generate_content(prompt)
        answer = response.text.strip()
        return answer, source_page, source_url, sources
    except Exception as e:
        print(f"LLM error: {e}")
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            return "I'm currently processing too many requests (API Quota Exceeded). Please try again in a minute.", None, None, []
        return f"Sorry, I encountered an error while processing your question: {error_msg}", None, None, []


async def answer_with_llm_knowledge(question: str, college_name: str) -> str:
    """
    Answer a question using the LLM's built-in knowledge.
    Used for general questions that don't require fresh website data.
    """
    prompt = f"""You are a college information assistant ONLY for {college_name}.

STRICT RULES:
1. ONLY answer questions about {college_name}
2. If the user asks about ANY other topic (other colleges, general topics, coding, jokes, etc.), respond ONLY with: "I can only answer questions about {college_name}. Please ask me about this college's history, location, rankings, courses, or other related information."
3. Be factual and accurate
4. If you're not sure about something, say so
5. For very specific/current data (like current fees, latest placements), recommend checking the official website
6. Be concise but informative
7. Do NOT engage in general conversation or off-topic discussions

QUESTION: {question}

If the question is about {college_name}, provide a helpful answer. If it's off-topic, politely redirect:"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"LLM knowledge error: {e}")
        return f"Sorry, I couldn't answer that question. Please try again."
