"""
Utility functions for the SEO Audit Agent.
"""

import re
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Optional, Tuple, Dict, Any
import validators
import tldextract

# Configure tldextract to use /tmp for cache (Vercel has read-only filesystem)
tld_extractor = tldextract.TLDExtract(cache_dir='/tmp/tldextract_cache')


def normalize_url(url: str) -> str:
    """Normalize a URL to a standard format."""
    url = url.strip()

    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    parsed = urlparse(url)

    # Ensure path ends consistently
    path = parsed.path if parsed.path else '/'

    return urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        path,
        parsed.params,
        parsed.query,
        ''  # Remove fragment
    ))


def is_valid_url(url: str) -> bool:
    """Check if a URL is valid."""
    try:
        result = validators.url(url)
        return result is True
    except Exception:
        return False


def get_domain(url: str) -> str:
    """Extract the domain from a URL."""
    extracted = tld_extractor(url)
    if extracted.subdomain:
        return f"{extracted.subdomain}.{extracted.domain}.{extracted.suffix}"
    return f"{extracted.domain}.{extracted.suffix}"


def get_base_domain(url: str) -> str:
    """Extract the base domain (without subdomain) from a URL."""
    extracted = tld_extractor(url)
    return f"{extracted.domain}.{extracted.suffix}"


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs belong to the same domain."""
    return get_domain(url1) == get_domain(url2)


def make_absolute_url(base_url: str, relative_url: str) -> str:
    """Convert a relative URL to an absolute URL."""
    return urljoin(base_url, relative_url)


def extract_text_content(html_content: str) -> str:
    """Extract plain text from HTML content."""
    # Remove script and style elements
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', ' ', clean)
    # Clean up whitespace
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def calculate_text_ratio(html_content: str) -> float:
    """Calculate the text-to-HTML ratio."""
    text = extract_text_content(html_content)
    if len(html_content) == 0:
        return 0.0
    return len(text) / len(html_content)


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to a maximum length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


class IssueCategory:
    """Categories for SEO issues."""
    CRITICAL = "critical"
    IMPORTANT = "important"
    RECOMMENDED = "recommended"


class IssuePriority:
    """Priority levels for issues."""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_milliseconds(ms: float) -> str:
    """Format milliseconds to human-readable format."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms/1000:.2f}s"
