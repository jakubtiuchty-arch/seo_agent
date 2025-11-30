"""
Crawlability Analyzer - Checks robots.txt, sitemaps, and indexation.
"""

import re
import requests
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from .base import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity, IssueCategory


class CrawlabilityAnalyzer(BaseAnalyzer):
    """Analyzer for crawlability-related SEO issues."""

    name = "crawlability"

    def __init__(self, url: str, html_content: str, response_headers: Dict[str, str],
                 session: Optional[requests.Session] = None):
        super().__init__(url, html_content, response_headers)
        self.session = session or requests.Session()
        self.parsed_url = urlparse(url)
        self.base_url = f"{self.parsed_url.scheme}://{self.parsed_url.netloc}"
        self.soup = BeautifulSoup(html_content, 'lxml')

    def analyze(self) -> AnalysisResult:
        """Perform crawlability analysis."""
        try:
            self._check_robots_txt()
            self._check_sitemap()
            self._check_meta_robots()
            self._check_canonical()
            self._check_x_robots_tag()
            self._check_noindex_issues()
            self._check_pagination()
            self.result.success = True
        except Exception as e:
            self.result.success = False
            self.result.error = str(e)

        return self.result

    def _fetch_url(self, url: str, timeout: int = 10) -> Tuple[Optional[str], int]:
        """Fetch a URL and return content and status code."""
        try:
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            return response.text, response.status_code
        except requests.RequestException:
            return None, 0

    def _check_robots_txt(self) -> None:
        """Check robots.txt file."""
        robots_url = urljoin(self.base_url, '/robots.txt')
        content, status_code = self._fetch_url(robots_url)

        self.result.data['robots_txt'] = {
            'url': robots_url,
            'exists': status_code == 200,
            'content': content if status_code == 200 else None
        }

        if status_code != 200:
            self.result.add_issue(SEOIssue(
                title="Missing robots.txt File",
                description="No robots.txt file found at the root of your domain. This file helps search engines understand which pages to crawl.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.CRAWLABILITY,
                impact="Search engines may crawl unnecessary pages, wasting crawl budget. You lose control over what gets indexed.",
                fix_steps=[
                    "Create a robots.txt file in your website's root directory",
                    "Add User-agent: * to apply rules to all crawlers",
                    "Specify Disallow rules for pages you don't want indexed (e.g., /admin/, /private/)",
                    "Add your sitemap URL: Sitemap: https://yourdomain.com/sitemap.xml",
                    "Upload the file to your server's root directory"
                ],
                expected_outcome="Search engines will respect your crawling preferences, optimizing crawl budget and preventing unwanted pages from being indexed.",
                validation_steps=[
                    f"Visit {robots_url} to confirm the file exists",
                    "Use Google Search Console's robots.txt Tester",
                    "Verify crawl stats improve in Search Console"
                ],
                difficulty="easy",
                priority_score=70
            ))
        else:
            # Check for common robots.txt issues
            if content:
                self._analyze_robots_content(content)

    def _analyze_robots_content(self, content: str) -> None:
        """Analyze robots.txt content for issues."""
        content_lower = content.lower()

        # Check if blocking all crawlers
        if 'disallow: /' in content_lower and 'disallow: /\n' in content_lower.replace(' ', ''):
            # Check if it's blocking everything
            lines = content_lower.split('\n')
            for i, line in enumerate(lines):
                if 'user-agent: *' in line:
                    # Check next non-empty lines for disallow: /
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if lines[j].strip() == 'disallow: /':
                            self.result.add_issue(SEOIssue(
                                title="Robots.txt Blocking All Crawlers",
                                description="Your robots.txt file contains 'Disallow: /' which blocks all search engine crawlers from accessing your site.",
                                severity=IssueSeverity.CRITICAL,
                                category=IssueCategory.CRAWLABILITY,
                                impact="Your website cannot be indexed by any search engine. You will have zero organic search visibility.",
                                fix_steps=[
                                    "Edit your robots.txt file",
                                    "Change 'Disallow: /' to allow crawling (remove the line or specify only directories to block)",
                                    "Example: Keep 'User-agent: *' but use specific Disallow rules like 'Disallow: /admin/'",
                                    "Save and upload the updated file"
                                ],
                                expected_outcome="Search engines will be able to crawl and index your site, restoring organic search visibility.",
                                validation_steps=[
                                    "Check robots.txt file content",
                                    "Use Google Search Console to request indexing",
                                    "Monitor index coverage report for improvements"
                                ],
                                difficulty="easy",
                                priority_score=100
                            ))
                            break

        # Check for sitemap declaration
        if 'sitemap:' not in content_lower:
            self.result.add_issue(SEOIssue(
                title="No Sitemap Declared in robots.txt",
                description="Your robots.txt doesn't include a Sitemap directive pointing to your XML sitemap.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.CRAWLABILITY,
                impact="Search engines may not discover your sitemap automatically, potentially missing important pages.",
                fix_steps=[
                    "Add a Sitemap directive to your robots.txt",
                    "Format: Sitemap: https://yourdomain.com/sitemap.xml",
                    "Place it at the end of your robots.txt file",
                    "If you have multiple sitemaps, add multiple Sitemap lines"
                ],
                expected_outcome="Search engines will easily discover and process your sitemap, improving page discovery.",
                validation_steps=[
                    "Verify the Sitemap line appears in robots.txt",
                    "Confirm the sitemap URL is accessible",
                    "Submit sitemap in Google Search Console"
                ],
                difficulty="easy",
                priority_score=40
            ))

    def _check_sitemap(self) -> None:
        """Check for XML sitemap."""
        sitemap_urls = [
            urljoin(self.base_url, '/sitemap.xml'),
            urljoin(self.base_url, '/sitemap_index.xml'),
            urljoin(self.base_url, '/sitemap/')
        ]

        sitemap_found = False
        for sitemap_url in sitemap_urls:
            content, status_code = self._fetch_url(sitemap_url)
            if status_code == 200 and content and ('<?xml' in content or '<urlset' in content or '<sitemapindex' in content):
                sitemap_found = True
                self.result.data['sitemap'] = {
                    'url': sitemap_url,
                    'exists': True
                }
                self._analyze_sitemap_content(content, sitemap_url)
                break

        if not sitemap_found:
            self.result.data['sitemap'] = {'exists': False}
            self.result.add_issue(SEOIssue(
                title="Missing XML Sitemap",
                description="No XML sitemap was found at common locations (/sitemap.xml, /sitemap_index.xml).",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.CRAWLABILITY,
                impact="Search engines rely on sitemaps to discover pages efficiently. Without one, some pages may never be found or indexed.",
                fix_steps=[
                    "Generate an XML sitemap using a tool or your CMS (WordPress, Yoast SEO, etc.)",
                    "Include all important pages with their last modification dates",
                    "Add priority hints for your most important pages",
                    "Upload sitemap.xml to your root directory",
                    "Submit the sitemap to Google Search Console and Bing Webmaster Tools"
                ],
                expected_outcome="Improved page discovery and faster indexing of new and updated content.",
                validation_steps=[
                    "Verify sitemap.xml is accessible at your domain root",
                    "Validate sitemap format using an XML validator",
                    "Check Google Search Console for sitemap status"
                ],
                difficulty="medium",
                priority_score=75
            ))

    def _analyze_sitemap_content(self, content: str, sitemap_url: str) -> None:
        """Analyze sitemap content for issues."""
        # Count URLs in sitemap
        url_count = content.count('<loc>')

        if url_count == 0:
            self.result.add_issue(SEOIssue(
                title="Empty Sitemap",
                description="Your sitemap exists but contains no URLs.",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.CRAWLABILITY,
                impact="An empty sitemap provides no value to search engines and may indicate a configuration problem.",
                fix_steps=[
                    "Review your sitemap generation process",
                    "Ensure all indexable pages are included",
                    "Regenerate the sitemap with your CMS or sitemap tool",
                    "Verify the sitemap contains URLs before uploading"
                ],
                expected_outcome="A properly populated sitemap that helps search engines discover all your important pages.",
                validation_steps=[
                    "Open sitemap.xml and verify it contains <loc> entries",
                    "Check sitemap status in Google Search Console"
                ],
                difficulty="medium",
                priority_score=85
            ))
        elif url_count > 50000:
            self.result.add_issue(SEOIssue(
                title="Sitemap Exceeds URL Limit",
                description=f"Your sitemap contains {url_count} URLs, exceeding the 50,000 URL limit per sitemap.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.CRAWLABILITY,
                impact="Search engines may not process all URLs in oversized sitemaps.",
                fix_steps=[
                    "Split your sitemap into multiple smaller sitemaps",
                    "Create a sitemap index file that references all individual sitemaps",
                    "Ensure each sitemap contains no more than 50,000 URLs",
                    "Update robots.txt to point to your sitemap index"
                ],
                expected_outcome="All URLs will be properly processed by search engines.",
                validation_steps=[
                    "Verify each sitemap has under 50,000 URLs",
                    "Confirm sitemap index is accessible",
                    "Check Google Search Console for processing status"
                ],
                difficulty="medium",
                priority_score=70
            ))

        self.result.data['sitemap']['url_count'] = url_count

    def _check_meta_robots(self) -> None:
        """Check meta robots tags."""
        meta_robots = self.soup.find('meta', attrs={'name': re.compile(r'^robots$', re.I)})

        if meta_robots:
            content = meta_robots.get('content', '').lower()
            self.result.data['meta_robots'] = content

            if 'noindex' in content:
                self.result.add_issue(SEOIssue(
                    title="Page Has noindex Meta Tag",
                    description=f"This page has a meta robots tag with 'noindex': {content}",
                    severity=IssueSeverity.CRITICAL,
                    category=IssueCategory.CRAWLABILITY,
                    impact="This page will not appear in search results. If this is your homepage or an important page, you're losing all organic traffic potential.",
                    fix_steps=[
                        "Locate the meta robots tag in your HTML <head> section",
                        "Remove 'noindex' from the content attribute",
                        "If you want to allow indexing: <meta name='robots' content='index, follow'>",
                        "Clear any caching layers and request re-indexing"
                    ],
                    expected_outcome="The page will become eligible for search engine indexing and can appear in search results.",
                    validation_steps=[
                        "View page source and verify meta robots tag is corrected",
                        "Use Google's URL Inspection tool to verify indexability",
                        "Request indexing in Search Console"
                    ],
                    current_value=content,
                    recommended_value="index, follow",
                    difficulty="easy",
                    priority_score=95
                ))

            if 'nofollow' in content:
                self.result.add_issue(SEOIssue(
                    title="Page Has nofollow Meta Tag",
                    description=f"This page has a meta robots tag with 'nofollow': {content}",
                    severity=IssueSeverity.IMPORTANT,
                    category=IssueCategory.CRAWLABILITY,
                    impact="Search engines won't follow links on this page, preventing link equity from flowing to linked pages.",
                    fix_steps=[
                        "Review if 'nofollow' is intentionally set",
                        "If not needed, remove 'nofollow' from the meta robots tag",
                        "Use rel='nofollow' on individual links instead if needed"
                    ],
                    expected_outcome="Link equity will flow naturally through the page's links, improving linked pages' rankings.",
                    validation_steps=[
                        "View page source and verify meta robots tag",
                        "Use SEO crawler to verify follow status"
                    ],
                    current_value=content,
                    difficulty="easy",
                    priority_score=60
                ))

    def _check_x_robots_tag(self) -> None:
        """Check X-Robots-Tag HTTP header."""
        x_robots = self.response_headers.get('X-Robots-Tag', '').lower()

        if x_robots:
            self.result.data['x_robots_tag'] = x_robots

            if 'noindex' in x_robots:
                self.result.add_issue(SEOIssue(
                    title="X-Robots-Tag Header Contains noindex",
                    description=f"The server is sending an X-Robots-Tag header with 'noindex': {x_robots}",
                    severity=IssueSeverity.CRITICAL,
                    category=IssueCategory.CRAWLABILITY,
                    impact="This page will not be indexed by search engines due to the HTTP header directive.",
                    fix_steps=[
                        "Access your web server configuration (Apache, Nginx, etc.)",
                        "Remove or modify the X-Robots-Tag header",
                        "For Apache: Remove 'Header set X-Robots-Tag' from .htaccess",
                        "For Nginx: Remove 'add_header X-Robots-Tag' from config",
                        "Restart your web server after changes"
                    ],
                    expected_outcome="The page will become eligible for indexing once the header is removed.",
                    validation_steps=[
                        "Check HTTP headers using browser dev tools or curl",
                        "Verify X-Robots-Tag header is no longer present",
                        "Request re-indexing in Search Console"
                    ],
                    current_value=x_robots,
                    difficulty="medium",
                    priority_score=95
                ))

    def _check_canonical(self) -> None:
        """Check canonical URL implementation."""
        canonical = self.soup.find('link', attrs={'rel': 'canonical'})

        self.result.data['canonical'] = {
            'exists': canonical is not None,
            'url': canonical.get('href') if canonical else None
        }

        if not canonical:
            self.result.add_issue(SEOIssue(
                title="Missing Canonical Tag",
                description="This page doesn't have a canonical URL specified.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.CRAWLABILITY,
                impact="Without a canonical tag, search engines may index duplicate versions of your page, diluting ranking signals.",
                fix_steps=[
                    "Add a canonical link tag to the <head> section",
                    f"Use: <link rel='canonical' href='{self.url}'>",
                    "Ensure the canonical URL is the preferred, absolute URL",
                    "Use self-referencing canonicals even for unique pages"
                ],
                expected_outcome="Search engines will consolidate ranking signals to your preferred URL version.",
                validation_steps=[
                    "View page source and verify canonical tag exists",
                    "Check Google Search Console URL Inspection",
                    "Verify canonical is the correct, preferred URL"
                ],
                recommended_value=self.url,
                difficulty="easy",
                priority_score=70
            ))
        else:
            canonical_url = canonical.get('href', '')
            # Check for common canonical issues
            if not canonical_url:
                self.result.add_issue(SEOIssue(
                    title="Empty Canonical Tag",
                    description="The canonical tag exists but has no href value.",
                    severity=IssueSeverity.CRITICAL,
                    category=IssueCategory.CRAWLABILITY,
                    impact="An empty canonical tag can confuse search engines and cause indexing issues.",
                    fix_steps=[
                        "Add the correct URL to the canonical tag's href attribute",
                        f"Example: <link rel='canonical' href='{self.url}'>"
                    ],
                    expected_outcome="Clear canonical signal for search engines.",
                    validation_steps=[
                        "View page source and verify canonical href is populated"
                    ],
                    difficulty="easy",
                    priority_score=85
                ))
            elif not canonical_url.startswith('http'):
                self.result.add_issue(SEOIssue(
                    title="Relative Canonical URL",
                    description=f"The canonical URL is relative: {canonical_url}",
                    severity=IssueSeverity.RECOMMENDED,
                    category=IssueCategory.CRAWLABILITY,
                    impact="While browsers resolve relative URLs, using absolute URLs for canonicals is best practice.",
                    fix_steps=[
                        "Change the canonical URL to an absolute URL",
                        f"Example: <link rel='canonical' href='{urljoin(self.base_url, canonical_url)}'>"
                    ],
                    expected_outcome="Clearer canonical signals without ambiguity.",
                    validation_steps=[
                        "Verify canonical URL starts with https://"
                    ],
                    current_value=canonical_url,
                    recommended_value=urljoin(self.base_url, canonical_url),
                    difficulty="easy",
                    priority_score=30
                ))

    def _check_noindex_issues(self) -> None:
        """Check for conflicting indexing signals."""
        has_noindex_meta = 'noindex' in self.result.data.get('meta_robots', '')
        has_noindex_header = 'noindex' in self.result.data.get('x_robots_tag', '')
        canonical = self.result.data.get('canonical', {})

        # Check for conflicting signals
        if (has_noindex_meta or has_noindex_header) and canonical.get('exists'):
            canonical_url = canonical.get('url', '')
            if canonical_url and canonical_url != self.url:
                self.result.add_issue(SEOIssue(
                    title="Conflicting Canonical and noindex Directives",
                    description="This page has both a noindex directive and a canonical pointing to a different URL.",
                    severity=IssueSeverity.IMPORTANT,
                    category=IssueCategory.CRAWLABILITY,
                    impact="Mixed signals can confuse search engines. noindex tells them not to index, while canonical suggests another URL should be indexed.",
                    fix_steps=[
                        "Decide if this page should be indexed or not",
                        "If not indexable: Keep noindex and remove canonical tag",
                        "If indexable: Remove noindex and keep proper canonical",
                        "If redirecting: Use 301 redirect instead of both signals"
                    ],
                    expected_outcome="Clear, consistent indexing signals for search engines.",
                    validation_steps=[
                        "Review page source for consistent directives",
                        "Use URL Inspection tool to verify interpretation"
                    ],
                    difficulty="medium",
                    priority_score=75
                ))

    def _check_pagination(self) -> None:
        """Check pagination implementation."""
        # Look for rel="next" and rel="prev"
        rel_next = self.soup.find('link', attrs={'rel': 'next'})
        rel_prev = self.soup.find('link', attrs={'rel': 'prev'})

        self.result.data['pagination'] = {
            'has_next': rel_next is not None,
            'has_prev': rel_prev is not None,
            'next_url': rel_next.get('href') if rel_next else None,
            'prev_url': rel_prev.get('href') if rel_prev else None
        }

        # Check for pagination patterns in URL
        pagination_patterns = [
            r'/page/\d+',
            r'\?page=\d+',
            r'&page=\d+',
            r'/p/\d+',
            r'\?p=\d+'
        ]

        is_paginated = any(re.search(pattern, self.url) for pattern in pagination_patterns)

        if is_paginated and not (rel_next or rel_prev):
            self.result.add_issue(SEOIssue(
                title="Paginated Page Missing rel=next/prev",
                description="This appears to be a paginated page but lacks rel='next' and/or rel='prev' link tags.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.CRAWLABILITY,
                impact="While Google no longer uses these for indexing decisions, they help crawlers understand page relationships.",
                fix_steps=[
                    "Add rel='prev' pointing to the previous page (if exists)",
                    "Add rel='next' pointing to the next page (if exists)",
                    "Use absolute URLs in these tags",
                    "Ensure consistent implementation across all paginated pages"
                ],
                expected_outcome="Better understanding of content structure by search engines.",
                validation_steps=[
                    "Check page source for rel='next' and rel='prev' tags",
                    "Verify URLs are correct and accessible"
                ],
                difficulty="medium",
                priority_score=25
            ))
