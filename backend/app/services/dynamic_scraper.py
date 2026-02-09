"""
Dynamic scraping service using Playwright.
Automatically discovers placement/career portals by analyzing page content.
Falls back to aggregator sites (Shiksha, Collegedunia, etc.) when official sites lack data.
"""

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote_plus
from typing import Optional, Dict, List
import re
import asyncio


# Limits
PAGE_TIMEOUT = 25000  # 25 seconds
CONTENT_LIMIT = 12000  # Max chars per page


# Aggregator sites for fallback (have actual placement data in HTML)
AGGREGATOR_SITES = {
    "placements": [
        "https://www.shiksha.com/college/{college_slug}-placements",
        "https://collegedunia.com/college/{college_slug}/placements",
        "https://www.careers360.com/colleges/{college_slug}/placements",
    ],
    "fees": [
        "https://www.shiksha.com/college/{college_slug}-fees",
        "https://collegedunia.com/college/{college_slug}/fee-structure",
        "https://www.careers360.com/colleges/{college_slug}/fees",
    ],
    "admissions": [
        "https://www.shiksha.com/college/{college_slug}-admissions",
        "https://collegedunia.com/college/{college_slug}/admission",
        "https://www.careers360.com/colleges/{college_slug}/admission",
    ],
    "facilities": [
        "https://www.shiksha.com/college/{college_slug}-infrastructure",
        "https://collegedunia.com/college/{college_slug}/hostel",
        "https://www.careers360.com/colleges/{college_slug}/facilities",
    ],
}


# Map intents to URL patterns for discovery
INTENT_URL_PATTERNS = {
    "placements": ["placement", "career", "ocs", "tpo", "recruit", "training"],
    "fees": ["fee", "tuition", "payment", "scholarship"],
    "admissions": ["admission", "apply", "eligibility", "intake"],
    "about": ["about", "overview", "history"],
    "facilities": ["hostel", "accommodation", "campus", "infrastructure", "facility", "amenity", "library", "mess"],
}

# Map intents to common paths (fallback)
INTENT_TO_PATHS = {
    "placements": ["/placements", "/placement", "/careers", "/ocs", "/tpo"],
    "fees": ["/fees", "/fee-structure", "/tuition"],
    "admissions": ["/admissions", "/admission", "/apply"],
    "about": ["/about", "/about-us", "/overview"],
    "facilities": ["/hostels", "/facilities", "/infrastructure", "/campus", "/amenities", "/campus-life"],
}


def extract_text_content(html: str) -> str:
    """Extract clean text from HTML."""
    soup = BeautifulSoup(html, "lxml")
    
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe", "form"]):
        element.decompose()
    
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) > 3]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    if len(text) > CONTENT_LIMIT:
        text = text[:CONTENT_LIMIT] + "..."
    
    return text


def discover_portal_urls(html: str, base_url: str, intent: str) -> List[str]:
    """
    Dynamically discover relevant portal URLs from page content.
    Looks for: iframes, subdomains, and links matching the intent.
    """
    discovered = []
    patterns = INTENT_URL_PATTERNS.get(intent, [])
    base_domain = urlparse(base_url).netloc.replace("www.", "")
    
    soup = BeautifulSoup(html, "lxml")
    
    # 1. Find iframes
    for iframe in soup.find_all("iframe", src=True):
        src = iframe.get("src", "")
        if src and not src.startswith(("data:", "javascript:", "about:")):
            if not src.startswith("http"):
                src = urljoin(base_url, src)
            discovered.append(("iframe", src))
    
    # 2. Find links to subdomains or matching URLs
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(strip=True).lower()
        
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        
        if not href.startswith("http"):
            href = urljoin(base_url, href)
        
        parsed = urlparse(href)
        link_domain = parsed.netloc.replace("www.", "")
        
        # Check if it's a subdomain of the base (e.g., ocs.iith.ac.in)
        is_subdomain = base_domain in link_domain and link_domain != base_domain
        
        # Check if URL or text matches intent patterns
        matches_pattern = any(p in href.lower() or p in text for p in patterns)
        
        if is_subdomain or matches_pattern:
            discovered.append(("link", href))
    
    # Deduplicate and prioritize
    seen = set()
    unique = []
    for source, url in discovered:
        if url not in seen:
            seen.add(url)
            unique.append((source, url))
    
    # Sort: iframes first, then subdomains, then regular links
    def priority(item):
        source, url = item
        parsed = urlparse(url)
        is_subdomain = base_domain in parsed.netloc and parsed.netloc != base_domain
        if source == "iframe":
            return 0
        elif is_subdomain:
            return 1
        else:
            return 2
    
    unique.sort(key=priority)
    
    return [url for _, url in unique[:5]]  # Return top 5


async def scrape_with_discovery(url: str, intent: str) -> Optional[str]:
    """
    Scrape a page and automatically discover better content sources.
    """
    print(f"🔍 Dynamic scrape: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            
            if not response or response.status >= 400:
                print(f"  ❌ HTTP {response.status if response else 'No response'}")
                await browser.close()
                return None
            
            await asyncio.sleep(2)
            
            html = await page.content()
            content = extract_text_content(html)
            
            # If content is low, discover and try better sources
            if len(content) < 500:
                print(f"  ⚠️ Low content ({len(content)} chars), discovering portals...")
                
                discovered_urls = discover_portal_urls(html, url, intent)
                
                for portal_url in discovered_urls:
                    print(f"  🔗 Trying discovered portal: {portal_url}")
                    
                    try:
                        await page.goto(portal_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                        await asyncio.sleep(2)
                        
                        # Try clicking relevant navigation in the portal
                        for selector in ['a:has-text("Stats")', 'a:has-text("Statistics")', 
                                         'button:has-text("Placement")', '.nav-link']:
                            try:
                                element = page.locator(selector).first
                                if await element.is_visible(timeout=500):
                                    await element.click()
                                    await asyncio.sleep(1)
                                    break
                            except:
                                pass
                        
                        portal_html = await page.content()
                        portal_content = extract_text_content(portal_html)
                        
                        if len(portal_content) > len(content):
                            content = portal_content
                            print(f"  📦 Got better content: {len(content)} chars")
                            break
                            
                    except Exception as e:
                        print(f"  ⚠️ Portal failed: {e}")
            
            await browser.close()
            
            if len(content) < 100:
                print(f"  ⚠️ Too little content ({len(content)} chars)")
                return None
            
            print(f"  ✅ Got {len(content)} chars")
            return content
            
        except asyncio.TimeoutError:
            print(f"  ⚠️ Timeout")
            await browser.close()
            return None
        except Exception as e:
            print(f"  ❌ Error: {e}")
            await browser.close()
            return None


async def scrape_for_intent(base_url: str, intent: str) -> Optional[Dict]:
    """
    Scrape the relevant page based on user's question intent.
    Strategy:
    1. First check homepage for subdomain links (e.g., campus.placements.iitb.ac.in)
    2. Then try standard paths (e.g., /placements)
    3. Use discovery to find embedded content
    """
    patterns = INTENT_URL_PATTERNS.get(intent, [])
    
    # Step 1: Scan homepage for subdomain portals first
    print(f"🔍 Scanning homepage for {intent} subdomains...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        
        try:
            await page.goto(base_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            await asyncio.sleep(2)
            
            html = await page.content()
            discovered_urls = discover_portal_urls(html, base_url, intent)
            
            await browser.close()
            
            # Try discovered subdomain portals first
            for portal_url in discovered_urls:
                if any(p in portal_url.lower() for p in patterns):
                    print(f"  🎯 Found matching portal: {portal_url}")
                    content = await scrape_with_discovery(portal_url, intent)
                    
                    if content and len(content) > 300:
                        return {
                            "page_type": intent,
                            "content_text": content,
                            "source_url": portal_url,
                        }
                        
        except Exception as e:
            print(f"  ⚠️ Homepage scan failed: {e}")
            try:
                await browser.close()
            except:
                pass
    
    # Step 2: Try standard paths
    paths = INTENT_TO_PATHS.get(intent, [])
    
    for path in paths:
        url = urljoin(base_url, path)
        content = await scrape_with_discovery(url, intent)
        
        if content and len(content) > 300:
            return {
                "page_type": intent,
                "content_text": content,
                "source_url": url,
            }
    
    # If no specific page found, try the base URL with discovery
    print(f"  ⚠️ No {intent} page found, trying base URL with discovery...")
    content = await scrape_with_discovery(base_url, intent)
    
    if content and len(content) > 200:
        return {
            "page_type": "general",
            "content_text": content,
            "source_url": base_url,
        }
    
    return None


async def quick_scrape_homepage(base_url: str) -> Optional[Dict]:
    """Quick scrape of just the homepage for initial confirmation."""
    print(f"🔍 Quick homepage scrape: {base_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        
        try:
            await page.goto(base_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            await asyncio.sleep(1.5)
            
            html = await page.content()
            content = extract_text_content(html)
            
            await browser.close()
            
            if content and len(content) > 100:
                return {
                    "page_type": "general",
                    "content_text": content,
                    "source_url": base_url,
                }
            return None
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            await browser.close()
            return None


from app.services.search import search_with_duckduckgo_lite, search_with_searxng
from app.services.dynamic_scraper import scrape_with_discovery, extract_text_content

async def scrape_from_aggregators(college_name: str, intent: str) -> Optional[Dict]:
    """
    Fallback: Search aggregator sites (Shiksha, Collegedunia, Careers360) for college data.
    Uses DDG/SearXNG to find the link, then scrapes that link directly.
    """
    if intent not in AGGREGATOR_SITES:
        return None
    
    print(f"🌐 Searching aggregator sites for {college_name} {intent}...")
    
    # Create search queries
    search_queries = [
        f"site:shiksha.com {college_name} {intent}",
        f"site:collegedunia.com {college_name} {intent}",
        f"site:careers360.com {college_name} {intent}",
    ]
    
    found_url = None
    
    # 1. Try finding a specific URL using our robust search service
    for query in search_queries:
        print(f"  🔍 Searching query: {query}")
        
        # Try DuckDuckGo first (fastest/most reliable)
        results = search_with_duckduckgo_lite(query, max_results=3)
        
        if not results:
             # Fallback to SearXNG
             results = search_with_searxng(query, max_results=3)
             
        if results:
            for res in results:
                href = res.get("href", "")
                if any(site in href for site in ['shiksha.com', 'collegedunia.com', 'careers360.com']):
                    # Check if it matches intent keywords to be sure
                    if intent in href.lower() or 'placement' in href.lower() or 'fees' in href.lower() or 'admission' in href.lower() or 'hostel' in href.lower() or 'infra' in href.lower():
                        found_url = href
                        print(f"  🎯 Found aggregator URL: {found_url}")
                        break
            if found_url:
                break
    
    if not found_url:
        print("  ⚠️ No relevant aggregator links found.")
        return None

    # 2. Scrape the specific URL found
    print(f"  🕷️ Scraping aggregator page: {found_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
             viewport={"width": 1280, "height": 720},
             user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        
        try:
            await page.goto(found_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2) # Wait for dynamic content
            
            # Scroll to load lazy content
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(1)
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(1)

            # Try to expand "Read More" sections common on these sites
            for selector in ['.read-more', '.view-more', 'button:has-text("Read More")', 'span:has-text("Read More")']:
                try:
                    elements = await page.locator(selector).all()
                    for el in elements[:3]: # Click first few
                        if await el.is_visible():
                            await el.click(timeout=1000)
                            await asyncio.sleep(0.5)
                except:
                    pass

            html = await page.content()
            content = extract_text_content(html)
            
            await browser.close()
            
            if content and len(content) > 500:
                print(f"  ✅ Got {len(content)} chars from aggregator")
                return {
                    "page_type": intent,
                    "content_text": content,
                    "source_url": found_url,
                }
            else:
                print(f"  ⚠️ Low content from aggregator ({len(content)} chars)")
                
        except Exception as e:
            print(f"  ⚠️ Aggregator scrape failed: {e}")
            await browser.close()
            
    return None
