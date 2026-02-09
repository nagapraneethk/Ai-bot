"""
Web scraping service using requests and BeautifulSoup.
Scrapes college websites for relevant information.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Set, Optional
import re
import time


# Page types to look for based on URL patterns
PAGE_TYPE_PATTERNS = {
    "about": ["about", "overview", "history", "vision", "mission", "profile"],
    "admissions": ["admission", "apply", "registration", "enrollment"],
    "academics": ["academic", "courses", "programs", "departments", "faculty", "curriculum"],
    "fees": ["fee", "tuition", "payment", "scholarship", "financial"],
    "placements": ["placement", "career", "recruitment", "companies", "internship"],
    "facilities": ["facility", "infrastructure", "campus", "hostel", "library", "lab"],
    "contact": ["contact", "address", "location", "reach"],
}

# Request headers to mimic a real browser more convincingly
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "Connection": "keep-alive",
}

# Maximum limits
MAX_PAGES = 20
REQUEST_TIMEOUT = 20
DELAY_BETWEEN_REQUESTS = 1.0

# Create a session for cookie persistence
def get_session():
    """Create a requests session with proper headers."""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def get_page_type(url: str) -> str:
    """Determine the page type based on URL patterns."""
    url_lower = url.lower()
    
    for page_type, patterns in PAGE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in url_lower:
                return page_type
    
    return "general"


def is_relevant_link(href: str, base_domain: str) -> bool:
    """Check if a link is relevant for scraping."""
    if not href:
        return False
        
    # Skip common irrelevant patterns
    skip_patterns = [
        ".pdf", ".doc", ".xls", ".ppt", ".zip", ".rar",
        ".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mp3",
        "javascript:", "mailto:", "tel:", "#",
        "login", "signin", "signup", "register",
        "facebook", "twitter", "linkedin", "instagram", "youtube",
    ]
    
    href_lower = href.lower()
    for pattern in skip_patterns:
        if pattern in href_lower:
            return False
    
    # Check if link contains relevant keywords
    relevant_keywords = []
    for patterns in PAGE_TYPE_PATTERNS.values():
        relevant_keywords.extend(patterns)
    
    return any(keyword in href_lower for keyword in relevant_keywords)


def extract_text_content(soup: BeautifulSoup) -> str:
    """Extract clean text from BeautifulSoup object."""
    # Remove script, style, nav, footer, header elements
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        element.decompose()
    
    # Get text
    text = soup.get_text(separator="\n", strip=True)
    
    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)
    
    # Remove excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Limit text length per page
    max_chars = 10000
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    
    return text


def fetch_page(url: str, session: requests.Session = None) -> Optional[BeautifulSoup]:
    """Fetch and parse a page with retry logic."""
    if session is None:
        session = get_session()
    
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            return None
            
        return BeautifulSoup(response.text, "lxml")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def get_internal_links(soup: BeautifulSoup, base_url: str) -> Set[str]:
    """Extract internal links from a page."""
    links = set()
    base_domain = urlparse(base_url).netloc
    
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        
        # Convert relative URLs to absolute
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        
        # Only keep internal links
        if parsed.netloc != base_domain:
            continue
            
        # Clean URL (remove fragments and query params for deduplication)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        if is_relevant_link(parsed.path, base_domain):
            links.add(clean_url)
    
    return links


def scrape_college_website(base_url: str) -> List[Dict]:
    """
    Scrape a college website for relevant information.
    
    Args:
        base_url: The homepage URL of the college website
        
    Returns:
        List of dicts with page_type, content_text, and source_url
    """
    scraped_pages = []
    visited_urls = set()
    urls_to_visit = {base_url}
    
    # Create session for cookie persistence across requests
    session = get_session()
    
    # First, visit the homepage to establish cookies
    print(f"Initializing session with {base_url}...")
    try:
        session.get(base_url, timeout=REQUEST_TIMEOUT)
        time.sleep(1)  # Small delay after initial request
    except Exception as e:
        print(f"Warning: Initial request failed: {e}")
    
    # Also add common paths
    common_paths = [
        "/about", "/about-us", "/about.html",
        "/admissions", "/admission",
        "/academics", "/courses", "/programs",
        "/placements", "/placement",
        "/fees", "/fee-structure",
        "/contact", "/contact-us",
    ]
    
    for path in common_paths:
        urls_to_visit.add(urljoin(base_url, path))
    
    while urls_to_visit and len(scraped_pages) < MAX_PAGES:
        url = urls_to_visit.pop()
        
        if url in visited_urls:
            continue
        visited_urls.add(url)
        
        # Fetch and parse page
        soup = fetch_page(url, session)
        if not soup:
            continue
            
        # Extract content
        content = extract_text_content(soup)
        if len(content) < 100:  # Skip pages with too little content
            continue
            
        page_type = get_page_type(url)
        
        # Check if we already have this page type with enough content
        existing_types = {p["page_type"] for p in scraped_pages}
        if page_type in existing_types and page_type != "general":
            continue
            
        scraped_pages.append({
            "page_type": page_type,
            "content_text": content,
            "source_url": url,
        })
        
        # Discover more links
        new_links = get_internal_links(soup, base_url)
        urls_to_visit.update(new_links - visited_urls)
        
        # Be polite
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    return scraped_pages
