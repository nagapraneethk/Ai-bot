"""
Web scraping service using Playwright for JavaScript-rendered pages.
Focused on essential college info: placements, fees, admissions, about.
"""

from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
import re
import asyncio


# Priority page types - these are what students care about most
PRIORITY_PAGES = ["placements", "fees", "admissions", "about"]

# Page type patterns (no faculty - too many pages!)
PAGE_TYPE_PATTERNS = {
    "placements": ["placement", "career", "recruitment", "companies", "package", "salary", "training"],
    "fees": ["fee", "tuition", "payment", "scholarship", "financial"],
    "admissions": ["admission", "apply", "eligibility", "cutoff", "entrance"],
    "about": ["about", "overview", "history", "vision", "mission"],
    "academics": ["academic", "course", "program"],  # Removed faculty, department
    "contact": ["contact", "address", "location"],
}

# Limits - keep it fast and focused
MAX_PAGES = 8  # Focus on key pages only
PAGE_TIMEOUT = 25000  # 25 seconds
CONTENT_LIMIT = 8000  # Max chars per page


def get_page_type(url: str) -> str:
    """Determine the page type based on URL patterns."""
    url_lower = url.lower()
    
    for page_type, patterns in PAGE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in url_lower:
                return page_type
    
    return "general"


def extract_text_content(html: str) -> str:
    """Extract clean text from HTML."""
    soup = BeautifulSoup(html, "lxml")
    
    # Remove non-content elements
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe", "form"]):
        element.decompose()
    
    # Get text
    text = soup.get_text(separator="\n", strip=True)
    
    # Clean up
    lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) > 3]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Limit length
    if len(text) > CONTENT_LIMIT:
        text = text[:CONTENT_LIMIT] + "..."
    
    return text


async def fetch_page(page: Page, url: str) -> Optional[str]:
    """Fetch a page with Playwright."""
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
        
        if not response or response.status >= 400:
            return None
        
        # Wait a bit for JS content
        await asyncio.sleep(1.5)
        
        return await page.content()
        
    except Exception as e:
        print(f"  Error: {e}")
        return None


async def scrape_college_website_playwright(base_url: str) -> List[Dict]:
    """
    Scrape essential pages from a college website.
    Focused on: placements, fees, admissions, about.
    """
    scraped_pages = []
    visited_urls = set()
    
    # Targeted URLs - only what matters
    target_paths = [
        # Placements (most important for students)
        "/placements", "/placement", "/careers", "/career", 
        "/training-placements", "/placement-cell", "/placements.php",
        # Fees
        "/fees", "/fee-structure", "/fee", "/tuition",
        # Admissions  
        "/admissions", "/admission", "/apply",
        # About
        "/about", "/about-us",
        # Homepage for general info
        "",
    ]
    
    urls_to_visit = [urljoin(base_url, path) for path in target_paths]
    
    print(f"🔍 Scraping {base_url} (focused mode)...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        )
        
        page = await context.new_page()
        
        for url in urls_to_visit:
            if url in visited_urls or len(scraped_pages) >= MAX_PAGES:
                continue
            visited_urls.add(url)
            
            page_type = get_page_type(url) if url != base_url else "general"
            
            # Skip if we already have this page type
            existing_types = {p["page_type"] for p in scraped_pages}
            if page_type in existing_types and page_type != "general":
                continue
            
            print(f"  📄 {page_type}: {url}")
            
            html = await fetch_page(page, url)
            if not html:
                continue
            
            content = extract_text_content(html)
            if len(content) < 200:  # Too little content
                continue
            
            scraped_pages.append({
                "page_type": page_type,
                "content_text": content,
                "source_url": url,
            })
            
            print(f"     ✓ {len(content)} chars")
            
            # Quick delay
            await asyncio.sleep(0.5)
            
            # Check if we have all priority pages
            found_types = {p["page_type"] for p in scraped_pages}
            if all(pt in found_types for pt in PRIORITY_PAGES):
                print("  ✅ All priority pages found!")
                break
        
        await browser.close()
    
    print(f"✅ Done! Scraped {len(scraped_pages)} pages.")
    return scraped_pages


# Sync wrapper
def scrape_college_website(base_url: str) -> List[Dict]:
    """Synchronous wrapper for the async Playwright scraper."""
    return asyncio.run(scrape_college_website_playwright(base_url))

