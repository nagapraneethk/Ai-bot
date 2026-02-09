"""
Website search service for finding official college websites.
Uses multiple search methods to ensure any college can be found.
"""

from urllib.parse import urlparse, quote_plus
from typing import List, Dict
import re
import httpx
from bs4 import BeautifulSoup
import time
import json
import os
import difflib


def load_colleges_database() -> Dict[str, Dict]:
    """Load colleges from JSON file into a dictionary for quick lookup."""
    colleges_dict = {}
    
    # Get the path to the colleges.json file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "..", "data", "colleges.json")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for college in data.get("colleges", []):
            key = college.get("key", "").lower().strip()
            if key:
                colleges_dict[key] = {
                    "name": college.get("name", ""),
                    "url": college.get("url", "")
                }
        
        print(f"Loaded {len(colleges_dict)} colleges from database")
        
    except FileNotFoundError:
        print(f"Warning: colleges.json not found at {json_path}")
    except json.JSONDecodeError as e:
        print(f"Warning: Error parsing colleges.json: {e}")
    except Exception as e:
        print(f"Warning: Error loading colleges database: {e}")
    
    return colleges_dict


def load_all_institutions() -> Dict[str, Dict]:
    """Load comprehensive list of Indian institutions from JSON."""
    institutions_dict = {}
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "..", "data", "all_institutions.json")
    
    try:
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f) # Expecting a list of dicts
                
            count = 0
            for item in data:
                # The format is a list of objects
                college_name = item.get("college", "")
                if college_name:
                    # Clean the name (remove Id: C-XXXXX)
                    clean_name = re.sub(r'\s*\(Id:.*?\)', '', college_name).strip()
                    key = clean_name.lower()
                    
                    institutions_dict[key] = {
                        "name": clean_name,
                        "university": item.get("university", ""),
                        "state": item.get("state", ""),
                        "district": item.get("district", ""),
                        "type": item.get("college_type", "")
                    }
                    count += 1
            
            print(f"Loaded {count} additional institutions from UGC database")
        else:
            print(f"UGC database not found at {json_path}")
            
    except Exception as e:
        print(f"Warning: Error loading UGC institutions: {e}")
        
    return institutions_dict


# Load databases at module startup
KNOWN_COLLEGES = load_colleges_database()
ALL_INSTITUTIONS = load_all_institutions()

# Aggregator domains to exclude
EXCLUDED_DOMAINS = [
    "collegedunia.com", "shiksha.com", "careers360.com", "getmyuni.com",
    "collegedekho.com", "justdial.com", "wikipedia.org", "youtube.com",
    "facebook.com", "twitter.com", "linkedin.com", "instagram.com",
    "quora.com", "reddit.com", "glassdoor.com", "naukri.com", "indeed.com",
    "studyabroad", "embibe.com", "byjus.com", "vedantu.com", "toppr.com",
    "leverage.edu", "admitkard.com", "collegesearch.in", "indiaeducation.net",
    "google.com", "bing.com", "duckduckgo.com",
]

# Preferred domain patterns for educational institutions
PREFERRED_PATTERNS = [r"\.ac\.in$", r"\.edu\.in$", r"\.edu$", r"\.org\.in$", r"\.res\.in$"]


def is_excluded_domain(domain: str) -> bool:
    """Check if domain is in exclusion list."""
    domain_lower = domain.lower()
    return any(excluded in domain_lower for excluded in EXCLUDED_DOMAINS)


def get_domain_confidence(url: str, college_name: str) -> str:
    """Determine confidence level for a URL being the official website."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # High confidence for educational domains
    for pattern in PREFERRED_PATTERNS:
        if re.search(pattern, domain):
            return "high"
    
    # Check if college name keywords appear in domain
    name_words = college_name.lower().split()
    significant_words = [w for w in name_words if len(w) > 3 and w not in ["of", "the", "and", "for", "institute", "university", "college"]]
    
    matches = sum(1 for word in significant_words if word in domain)
    if matches >= 2:
        return "high"
    elif matches >= 1:
        return "medium"
    return "low"


def search_known_colleges(college_name: str) -> List[Dict]:
    """Search in our known colleges database (instant lookup) and UGC database."""
    name_lower = college_name.lower().strip()
    
    # 1. Direct match in KNOWN_COLLEGES (Best case: we have the URL)
    if name_lower in KNOWN_COLLEGES:
        info = KNOWN_COLLEGES[name_lower]
        return [{
            "name": info["name"],
            "url": info["url"],
            "confidence": "high",
            "source": "database"
        }]
        
    # 2. Direct match in ALL_INSTITUTIONS (Good case: we know it exists, but need to search web)
    if name_lower in ALL_INSTITUTIONS:
        info = ALL_INSTITUTIONS[name_lower]
        return [{
            "name": info["name"],
            "url": "",  # Empty URL signals need for web search
            "confidence": "high",
            "source": "ugc_database",
            "details": f"{info['district']}, {info['state']}"
        }]

    matches = []
    
    # 3. Fuzzy match in KNOWN_COLLEGES
    # Check for significant word overlap
    query_words = set(re.findall(r'\w+', name_lower))
    query_words = {w for w in query_words if len(w) > 3}
    
    for key, info in KNOWN_COLLEGES.items():
        if name_lower in key or key in name_lower:
            matches.append({
                "name": info["name"],
                "url": info["url"],
                "confidence": "high",
                "source": "database"
            })
            continue
            
        # Word overlap check
        key_words = set(re.findall(r'\w+', key))
        common = query_words.intersection(key_words)
        if len(common) >= 2:  # At least 2 significant words match
            matches.append({
                "name": info["name"],
                "url": info["url"],
                "confidence": "medium",
                "source": "database"
            })
            
    if matches:
        return sorted(matches, key=lambda x: x['confidence'], reverse=True)[:5]
        
    # 4. Fuzzy match in ALL_INSTITUTIONS
    # Use token-based matching which is more robust for partial names than difflib
    ugc_matches = []
    
    # Optimization: limit iterations if we find good matches early or use smart filtering
    # For 40k items, a simple loop is acceptable (~50ms) but we should be careful with complex operations
    current_matches = 0
    
    for key, info in ALL_INSTITUTIONS.items():
        score = 0
        
        # Exact prefix match is very strong
        if key.startswith(name_lower):
            score = 90
        # Substring match
        elif name_lower in key:
            score = 80
        else:
            # Token overlap check
            # Only checking if we haven't found enough high-quality matches yet
            if current_matches < 10:
                key_words = set(re.findall(r'\w+', key))
                common = len(query_words.intersection(key_words))
                if common >= 2:  # At least 2 significant words match
                    score = 60 + common
        
        if score > 0:
            ugc_matches.append({
                "name": info["name"],
                "url": "",
                "confidence": "medium",
                "source": "ugc_database",
                "details": f"{info['district']}, {info['state']}",
                "score": score
            })
            if score >= 80:
                current_matches += 1
                
    # Sort by score and take top 5
    if ugc_matches:
        ugc_matches.sort(key=lambda x: x['score'], reverse=True)
        matches.extend(ugc_matches[:5])

    return matches


def get_http_client():
    """Get configured HTTP client with browser-like settings."""
    return httpx.Client(
        timeout=15.0,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )


def search_with_searxng(query: str, max_results: int = 10) -> List[Dict]:
    """Search using public SearXNG instances (meta-search that aggregates Google, Bing, etc.)."""
    searxng_instances = [
        "https://searx.tiekoetter.com",
        "https://searx.fmac.aa.net.uk",
        "https://search.ononoki.org",
        "https://opnxng.com",
        "https://search.sapti.me",
    ]
    
    for instance in searxng_instances:
        try:
            with get_http_client() as client:
                url = f"{instance}/search"
                params = {
                    "q": query,
                    "format": "json",
                    "categories": "general",
                }
                response = client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                results = []
                
                for item in data.get("results", []):
                    href = item.get("url", "")
                    title = item.get("title", "")
                    
                    if href and href.startswith("http"):
                        parsed = urlparse(href)
                        if not is_excluded_domain(parsed.netloc):
                            results.append({
                                "href": f"{parsed.scheme}://{parsed.netloc}",
                                "title": title,
                            })
                    
                    if len(results) >= max_results:
                        break
                
                if results:
                    print(f"SearXNG ({instance}) returned {len(results)} results")
                    return results
                    
        except Exception as e:
            print(f"SearXNG {instance} error: {e}")
            continue
    
    return []


def search_with_startpage(query: str, max_results: int = 10) -> List[Dict]:
    """Search using Startpage (Google proxy)."""
    try:
        with get_http_client() as client:
            # First get the search form to get CSRF token
            home_response = client.get("https://www.startpage.com/")
            
            # Now make the search request
            url = "https://www.startpage.com/sp/search"
            data = {"query": query}
            response = client.post(url, data=data)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            results = []
            
            for item in soup.select(".w-gl__result"):
                link = item.select_one("a.w-gl__result-url")
                title_elem = item.select_one("h3")
                
                if link and title_elem:
                    href = link.get("href", "")
                    title = title_elem.get_text(strip=True)
                    
                    if href.startswith("http"):
                        parsed = urlparse(href)
                        if not is_excluded_domain(parsed.netloc):
                            results.append({
                                "href": f"{parsed.scheme}://{parsed.netloc}",
                                "title": title,
                            })
                
                if len(results) >= max_results:
                    break
            
            print(f"Startpage returned {len(results)} results")
            return results
            
    except Exception as e:
        print(f"Startpage search error: {e}")
        return []


def search_with_duckduckgo_lite(query: str, max_results: int = 10) -> List[Dict]:
    """Search using DuckDuckGo Lite (simpler version, less likely to be blocked)."""
    try:
        with get_http_client() as client:
            url = "https://lite.duckduckgo.com/lite/"
            data = {"q": query}
            response = client.post(url, data=data)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            results = []
            
            # DuckDuckGo Lite uses table rows
            for row in soup.select("tr"):
                link = row.select_one("a.result-link")
                if link:
                    href = link.get("href", "")
                    title = link.get_text(strip=True)
                    
                    if href.startswith("http"):
                        parsed = urlparse(href)
                        if not is_excluded_domain(parsed.netloc):
                            results.append({
                                "href": f"{parsed.scheme}://{parsed.netloc}",
                                "title": title,
                            })
                
                if len(results) >= max_results:
                    break
            
            print(f"DuckDuckGo Lite returned {len(results)} results")
            return results
            
    except Exception as e:
        print(f"DuckDuckGo Lite error: {e}")
        return []


def search_with_playwright_google(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search Google using Playwright as a fallback.
    Most reliable but slower.
    """
    import asyncio
    from playwright.async_api import async_playwright
    
    async def _search():
        results = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                # Use Google search
                search_url = f"https://www.google.com/search?q={quote_plus(query)}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(1)
                
                # Extract search results
                html = await page.content()
                await browser.close()
                
                soup = BeautifulSoup(html, 'lxml')
                
                # Find all search result links
                seen_domains = set()
                for a in soup.find_all('a', href=True):
                    href = a.get('href', '')
                    
                    # Google wraps links in /url?q=... format
                    if href.startswith('/url?q='):
                        href = href.split('/url?q=')[1].split('&')[0]
                    
                    if not href.startswith('http'):
                        continue
                    
                    parsed = urlparse(href)
                    domain = parsed.netloc.replace('www.', '')
                    
                    # Skip excluded domains and duplicates
                    if is_excluded_domain(domain) or domain in seen_domains:
                        continue
                    
                    # Focus on .edu, .ac.in domains for colleges
                    if '.edu' in domain or '.ac.in' in domain or 'college' in domain:
                        seen_domains.add(domain)
                        results.append({
                            "href": f"{parsed.scheme}://{parsed.netloc}",
                            "title": a.get_text(strip=True) or domain
                        })
                        
                        if len(results) >= max_results:
                            break
                
        except Exception as e:
            print(f"Playwright Google search error: {e}")
        
        return results
    
    # Run async function
    # Run async function
    try:
        # Check if event loop is already running
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        if loop and loop.is_running():
            # If loop is running, create a new one for this synchronous operation
            # usage of nest_asyncio would be better, but this is a fallback
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(_search())
            finally:
                new_loop.close()
                # Restore original loop if needed (optional since we are likely in a separate thread context if this block is hit)
                asyncio.set_event_loop(loop)
        else:
            return asyncio.run(_search())
            
    except Exception as e:
        print(f"Error running Playwright search: {e}")
        return []


def search_college_website(college_name: str, max_results: int = 5, force_web_search: bool = False) -> List[Dict]:
    """
    Search for official college website using multiple methods.
    Works for ANY college, not just the hardcoded ones.
    
    Args:
        college_name: Name of the college to search for
        max_results: Maximum number of results to return
        force_web_search: If True, skip known colleges and search the web directly
    """
    candidates = []
    
    # Step 1: Check known colleges database (instant) - unless force_web_search is True
    if not force_web_search:
        known_results = search_known_colleges(college_name)
        
        # Check if we have results with URLs (from KNOWN_COLLEGES)
        has_url = any(r.get("url") for r in known_results)
        
        if has_url:
            print(f"Found {len(known_results)} match(es) in known colleges database")
            return [r for r in known_results if r.get("url")][:max_results]
            
        # If we have matches without URLs (from UGC database), use them to refine the search
        if known_results:
            best_match = known_results[0]
            if best_match.get("source") == "ugc_database":
                print(f"Found in UGC database: {best_match['name']}. Searching for official website...")
                # Update college_name to be more specific for the web search
                college_name = f"{best_match['name']} {best_match.get('details', '')}"
    else:
        print(f"Force web search enabled, skipping known colleges database")
    
    print(f"Not in known database, searching web for: {college_name}")
    
    # Optimized search query
    query = f"{college_name} official website"
    
    # Step 2: Try SearXNG first (aggregates multiple search engines)
    print("Trying SearXNG meta-search...")
    results = search_with_searxng(query, max_results * 2)
    
    # Step 3: Fallback to Startpage (Google proxy)
    if not results:
        print("SearXNG failed, trying Startpage...")
        time.sleep(0.5)
        results = search_with_startpage(query, max_results * 2)
    
    # Step 4: Fallback to DuckDuckGo Lite
    if not results:
        print("Startpage failed, trying DuckDuckGo Lite...")
        time.sleep(0.5)
        results = search_with_duckduckgo_lite(query, max_results * 2)
    
    # Step 5: Final fallback - Playwright Google search (most reliable)
    if not results:
        print("All text-based search failed, trying Playwright Google search...")
        results = search_with_playwright_google(query, max_results)
    
    if not results:
        print("All search methods failed")
        return []
    
    # Process and deduplicate results
    seen_domains = set()
    for result in results:
        url = result.get("href", "")
        title = result.get("title", "")
        
        if not url:
            continue
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if not domain:
                continue
        except:
            continue
        
        # Skip duplicates (by base domain)
        base_domain = ".".join(domain.split(".")[-2:]) if "." in domain else domain
        if base_domain in seen_domains:
            continue
        seen_domains.add(base_domain)
        
        # Calculate confidence
        confidence = get_domain_confidence(url, college_name)
        
        candidates.append({
            "name": title or f"{college_name} - {domain}",
            "url": url,
            "confidence": confidence
        })
        
        if len(candidates) >= max_results:
            break
    
    # Sort by confidence (high first)
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    candidates.sort(key=lambda x: confidence_order.get(x["confidence"], 3))
    
    print(f"Found {len(candidates)} candidate(s)")
    return candidates[:max_results]
