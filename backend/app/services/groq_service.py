"""
Groq LLM Service using Llama-3-70b/Mixtral.
High speed, generous free tier.
"""

import os
from groq import Groq
from typing import Tuple, Optional, List
from app.config import get_settings

settings = get_settings()

client = None
if settings.groq_api_key:
    client = Groq(api_key=settings.groq_api_key)

MODEL = "llama-3.3-70b-versatile"

async def classify_question_groq(question: str) -> Tuple[bool, str]:
    """Classify question intent using Groq."""
    if not client:
        return True, "general"

    prompt = f"""Classify this question about a college.

QUESTION: "{question}"

Determine:
1. Does this question need CURRENT/SPECIFIC data from the college website? (placement stats, fee amounts, admission cutoffs)
2. Or can it be answered from GENERAL KNOWLEDGE? (history, location, rankings, famous alumni)

Respond in EXACTLY this format (one line only):
SCRAPE:<yes/no>|INTENT:<placements/fees/admissions/about/general>

Examples:
- "What is the highest package?" → SCRAPE:yes|INTENT:placements
- "When was it founded?" → SCRAPE:no|INTENT:about
- "Fee structure?" → SCRAPE:yes|INTENT:fees

Your response:"""

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=50
        )
        result = completion.choices[0].message.content.strip().upper()
        
        if "SCRAPE:" in result and "INTENT:" in result:
            parts = result.split("|")
            scrape_part = parts[0].replace("SCRAPE:", "").strip()
            intent_part = parts[1].replace("INTENT:", "").strip().lower()
            
            needs_scrape = scrape_part == "YES"
            intent = intent_part if intent_part in ["placements", "fees", "admissions", "about", "general"] else "general"
            return needs_scrape, intent
            
    except Exception as e:
        print(f"Groq classification error: {e}")
    
    return True, "general"

async def answer_question_groq(question: str, context: str, college_name: str) -> str:
    """Answer user question using Groq with scraped context."""
    if not client:
        return "Groq API key not configured."

    prompt = f"""You are a helpful assistant for {college_name}.

CONTEXT FROM OFFICIAL WEBSITE:
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer the user's question about {college_name} directly and helpfully.
2. The CONTEXT may contain data from OFFICIAL WEBSITES and AGGREGATORS (like Shiksha, Collegedunia).
3. SYNTHESIZE the answer by combining these sources. If the official site lacks data, rely on the aggregator data.
4. IF specific details are still missing, USE YOUR OWN KNOWLEDGE base to provide the answer (e.g., "Approximately ₹1.5 - 2 Lakhs per year").
5. AVOID saying "I couldn't find details" or "Visit the website". Instead, give the best available information you have.
6. Format the answer with bullet points if possible.
7. DO NOT use emojis in your response.

Answer:"""

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating answer: {str(e)}"

async def answer_with_knowledge_groq(question: str, college_name: str) -> str:
    """Answer using Groq's internal knowledge (Llama-3)."""
    if not client:
        return "Groq API key not configured."

    prompt = f"""You are an expert on {college_name}.
Answer the following question accurately.

QUESTION: {question} (specifically regarding {college_name})

Answer:"""

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating answer: {str(e)}"
