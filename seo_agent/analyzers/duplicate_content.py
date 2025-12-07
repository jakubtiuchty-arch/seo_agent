"""
Duplicate Content Analyzer - Checks for duplicate content signals and canonicalization issues.
"""

import re
import hashlib
from typing import Dict, List, Set
from urllib.parse import urlparse, urljoin, parse_qs
from bs4 import BeautifulSoup

from .base import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity, IssueCategory


class DuplicateContentAnalyzer(BaseAnalyzer):
    """Analyzer for duplicate content detection and canonicalization."""

    name = "duplicate_content"

    def __init__(self, url: str, html_content: str, response_headers: Dict[str, str]):
        super().__init__(url, html_content, response_headers)
        self.soup = BeautifulSoup(html_content, 'lxml')
        self.parsed_url = urlparse(url)

    def analyze(self) -> AnalysisResult:
        """Perform duplicate content analysis."""
        try:
            self._check_canonical_implementation()
            self._check_hreflang_tags()
            self._check_url_parameters()
            self._check_content_uniqueness()
            self._check_www_consistency()
            self._check_trailing_slash_consistency()
            self._check_duplicate_meta_tags()
            self.result.success = True
        except Exception as e:
            self.result.success = False
            self.result.error = str(e)

        return self.result

    def _check_canonical_implementation(self) -> None:
        """Check canonical tag implementation thoroughly."""
        canonical = self.soup.find('link', attrs={'rel': 'canonical'})

        if not canonical:
            self.result.data['canonical'] = {'exists': False}
            self.result.add_issue(SEOIssue(
                title="Missing Canonical Tag",
                description="No canonical URL specified for this page.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.CRAWLABILITY,
                impact="Without a canonical tag, search engines may index duplicate versions, diluting ranking signals.",
                fix_steps=[
                    "Add a self-referencing canonical tag to every page",
                    f"<link rel='canonical' href='{self.url}'>",
                    "Place it in the <head> section",
                    "Use absolute URLs, not relative paths"
                ],
                expected_outcome="Search engines consolidate ranking signals to preferred URL.",
                validation_steps=[
                    "View page source and verify canonical exists",
                    "Use Google Search Console URL Inspection",
                    "Check that canonical URL is your preferred version"
                ],
                recommended_value=self.url,
                difficulty="easy",
                priority_score=70
            ))
            return

        canonical_url = canonical.get('href', '').strip()
        self.result.data['canonical'] = {
            'exists': True,
            'url': canonical_url
        }

        # Check for empty canonical
        if not canonical_url:
            self.result.add_issue(SEOIssue(
                title="Empty Canonical Tag",
                description="Canonical tag exists but has no href value.",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.CRAWLABILITY,
                impact="Empty canonical provides no guidance and may cause indexing confusion.",
                fix_steps=[
                    "Add the correct URL to the canonical href",
                    f"Example: <link rel='canonical' href='{self.url}'>"
                ],
                expected_outcome="Clear canonical signal for search engines.",
                validation_steps=[
                    "Verify canonical href has a valid URL"
                ],
                difficulty="easy",
                priority_score=90
            ))
            return

        # Check for relative canonical
        if not canonical_url.startswith(('http://', 'https://')):
            absolute_canonical = urljoin(self.url, canonical_url)
            self.result.add_issue(SEOIssue(
                title="Relative Canonical URL",
                description=f"Canonical uses relative URL: {canonical_url}",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.CRAWLABILITY,
                impact="While browsers resolve relative URLs, absolute URLs are clearer and recommended.",
                fix_steps=[
                    "Change canonical to use absolute URL",
                    f"Example: <link rel='canonical' href='{absolute_canonical}'>"
                ],
                expected_outcome="Unambiguous canonical signal.",
                validation_steps=[
                    "Verify canonical starts with https://"
                ],
                current_value=canonical_url,
                recommended_value=absolute_canonical,
                difficulty="easy",
                priority_score=30
            ))
        else:
            # Check for protocol mismatch
            canonical_parsed = urlparse(canonical_url)
            if canonical_parsed.scheme != self.parsed_url.scheme:
                self.result.add_issue(SEOIssue(
                    title="Canonical Protocol Mismatch",
                    description=f"Page uses {self.parsed_url.scheme}:// but canonical points to {canonical_parsed.scheme}://",
                    severity=IssueSeverity.IMPORTANT,
                    category=IssueCategory.CRAWLABILITY,
                    impact="Protocol mismatch in canonical can cause indexing issues.",
                    fix_steps=[
                        "Ensure canonical uses the same protocol as the page",
                        f"If using HTTPS, canonical should be: {canonical_url.replace('http://', 'https://')}"
                    ],
                    expected_outcome="Consistent protocol in canonical and page URL.",
                    validation_steps=[
                        "Verify canonical protocol matches page protocol"
                    ],
                    current_value=canonical_url,
                    difficulty="easy",
                    priority_score=65
                ))

            # Check for domain mismatch (cross-domain canonical)
            if canonical_parsed.netloc.lower() != self.parsed_url.netloc.lower():
                self.result.add_issue(SEOIssue(
                    title="Cross-Domain Canonical Detected",
                    description=f"Canonical points to different domain: {canonical_parsed.netloc}",
                    severity=IssueSeverity.IMPORTANT,
                    category=IssueCategory.CRAWLABILITY,
                    impact="Cross-domain canonicals transfer ranking signals to another domain. Verify this is intentional.",
                    fix_steps=[
                        "Verify the cross-domain canonical is correct",
                        "If unintentional, update to point to current domain",
                        "Cross-domain canonicals are valid for syndicated content"
                    ],
                    expected_outcome="Intentional canonical configuration.",
                    validation_steps=[
                        "Confirm cross-domain canonical is intentional",
                        "Check both domains in Search Console"
                    ],
                    current_value=canonical_url,
                    difficulty="easy",
                    priority_score=75
                ))

    def _check_hreflang_tags(self) -> None:
        """Check hreflang implementation for international SEO."""
        hreflang_tags = self.soup.find_all('link', attrs={'rel': 'alternate', 'hreflang': True})

        self.result.data['hreflang'] = {
            'count': len(hreflang_tags),
            'languages': [tag.get('hreflang') for tag in hreflang_tags]
        }

        if not hreflang_tags:
            # Not necessarily an issue - only relevant for multi-language sites
            return

        # Check for x-default
        has_x_default = any(tag.get('hreflang') == 'x-default' for tag in hreflang_tags)

        if not has_x_default:
            self.result.add_issue(SEOIssue(
                title="Missing x-default Hreflang",
                description="Hreflang tags present but missing x-default fallback.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.CRAWLABILITY,
                impact="x-default helps search engines handle users whose language isn't specifically targeted.",
                fix_steps=[
                    "Add x-default hreflang pointing to your main/fallback version",
                    "<link rel='alternate' hreflang='x-default' href='https://example.com/'>",
                    "Usually points to English version or language selector page"
                ],
                expected_outcome="Better handling of international users in search.",
                validation_steps=[
                    "Verify x-default hreflang exists",
                    "Confirm it points to appropriate fallback page"
                ],
                difficulty="easy",
                priority_score=35
            ))

        # Check for self-referencing hreflang
        current_url_normalized = self.url.rstrip('/')
        has_self_reference = False
        for tag in hreflang_tags:
            href = tag.get('href', '').rstrip('/')
            if href == current_url_normalized:
                has_self_reference = True
                break

        if not has_self_reference and len(hreflang_tags) > 0:
            self.result.add_issue(SEOIssue(
                title="Hreflang Missing Self-Reference",
                description="This page has hreflang tags but doesn't reference itself.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.CRAWLABILITY,
                impact="Hreflang clusters must include self-referencing for proper interpretation.",
                fix_steps=[
                    "Add a hreflang tag that references this page's URL",
                    "Each page in the hreflang cluster must reference all others including itself"
                ],
                expected_outcome="Complete hreflang implementation.",
                validation_steps=[
                    "Verify page URL appears in its own hreflang tags",
                    "Use hreflang testing tools"
                ],
                difficulty="easy",
                priority_score=60
            ))

    def _check_url_parameters(self) -> None:
        """Check for URL parameters that might cause duplicate content."""
        query_string = self.parsed_url.query
        params = parse_qs(query_string) if query_string else {}

        # Common tracking/sorting parameters that shouldn't affect content
        tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                          'ref', 'source', 'campaign', 'gclid', 'fbclid', 'msclkid']
        sorting_params = ['sort', 'order', 'orderby', 'sortby', 'dir', 'direction']
        session_params = ['sid', 'session', 'jsessionid', 'phpsessid']

        found_tracking = [p for p in params if p.lower() in tracking_params]
        found_sorting = [p for p in params if p.lower() in sorting_params]
        found_session = [p for p in params if p.lower() in session_params]

        self.result.data['url_parameters'] = {
            'total_params': len(params),
            'tracking_params': found_tracking,
            'sorting_params': found_sorting,
            'session_params': found_session
        }

        if found_session:
            self.result.add_issue(SEOIssue(
                title="Session ID in URL",
                description=f"URL contains session parameter(s): {', '.join(found_session)}",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.CRAWLABILITY,
                impact="Session IDs in URLs create infinite duplicate URLs - one per visitor session.",
                fix_steps=[
                    "Use cookies instead of URL parameters for session tracking",
                    "If URL sessions are required, use canonical to point to sessionless URL",
                    "Configure Google Search Console URL Parameters tool",
                    "Block session parameters in robots.txt"
                ],
                expected_outcome="Clean URLs without session pollution.",
                validation_steps=[
                    "Verify session IDs don't appear in URLs",
                    "Check canonical points to clean URL"
                ],
                current_value=f"Session params: {', '.join(found_session)}",
                difficulty="medium",
                priority_score=90
            ))

        if found_tracking and not self.result.data.get('canonical', {}).get('exists'):
            self.result.add_issue(SEOIssue(
                title="Tracking Parameters Without Canonical",
                description=f"URL has tracking parameters but no canonical: {', '.join(found_tracking)}",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.CRAWLABILITY,
                impact="Tracking parameters create duplicate URLs. Without canonical, each variant may be indexed.",
                fix_steps=[
                    "Add canonical tag pointing to the URL without tracking parameters",
                    "Configure Google Search Console to ignore tracking parameters",
                    "Or use # fragment for tracking (e.g., #utm_source=...)"
                ],
                expected_outcome="Single canonical version indexed despite tracking parameters.",
                validation_steps=[
                    "Verify canonical excludes tracking parameters",
                    "Check Search Console for parameter handling"
                ],
                difficulty="easy",
                priority_score=65
            ))

    def _check_content_uniqueness(self) -> None:
        """Check for indicators of duplicate or thin content."""
        # Get main content
        main_content = self._extract_main_content()
        content_hash = hashlib.md5(main_content.encode()).hexdigest()

        word_count = len(main_content.split())

        self.result.data['content'] = {
            'word_count': word_count,
            'content_hash': content_hash[:16]
        }

        # Check for boilerplate dominance
        full_text = self.soup.get_text()
        full_word_count = len(full_text.split())

        if full_word_count > 0:
            unique_ratio = word_count / full_word_count
            self.result.data['content']['unique_ratio'] = round(unique_ratio, 2)

            if unique_ratio < 0.2 and word_count < 200:
                self.result.add_issue(SEOIssue(
                    title="Low Unique Content Ratio",
                    description=f"Only {word_count} words of unique content ({unique_ratio:.0%} of total).",
                    severity=IssueSeverity.IMPORTANT,
                    category=IssueCategory.PAGE_CONTENT,
                    impact="Pages with mostly boilerplate and little unique content may be seen as thin or duplicate.",
                    fix_steps=[
                        "Add more unique, valuable content to the page",
                        "Reduce template/boilerplate content where possible",
                        "Ensure each page offers distinct value",
                        "Consider if this page should be noindexed or consolidated"
                    ],
                    expected_outcome="Higher proportion of unique, valuable content.",
                    validation_steps=[
                        "Review page for unique content value",
                        "Compare against similar pages on site"
                    ],
                    current_value=f"{word_count} unique words ({unique_ratio:.0%})",
                    difficulty="medium",
                    priority_score=55
                ))

    def _extract_main_content(self) -> str:
        """Extract main content area, excluding navigation/footer."""
        # Try to find main content area
        main_selectors = [
            self.soup.find('main'),
            self.soup.find('article'),
            self.soup.find(id=re.compile(r'content|main', re.I)),
            self.soup.find(class_=re.compile(r'content|main|article', re.I))
        ]

        for selector in main_selectors:
            if selector:
                return selector.get_text(strip=True)

        # Fallback: remove nav, header, footer, sidebar
        soup_copy = BeautifulSoup(str(self.soup), 'lxml')
        for element in soup_copy.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style']):
            element.decompose()

        return soup_copy.get_text(strip=True)

    def _check_www_consistency(self) -> None:
        """Check for www/non-www consistency in links."""
        current_has_www = self.parsed_url.netloc.startswith('www.')

        all_links = self.soup.find_all('a', href=True)
        inconsistent_links = []

        base_domain = self.parsed_url.netloc.replace('www.', '')

        for link in all_links:
            href = link.get('href', '')
            if href.startswith('http'):
                link_parsed = urlparse(href)
                link_domain = link_parsed.netloc.lower()

                # Check if it's the same site
                if base_domain in link_domain or link_domain.replace('www.', '') == base_domain:
                    link_has_www = link_domain.startswith('www.')
                    if link_has_www != current_has_www:
                        inconsistent_links.append(href[:80])

        if inconsistent_links:
            self.result.data['www_consistency'] = {
                'inconsistent_count': len(inconsistent_links)
            }

            self.result.add_issue(SEOIssue(
                title="Inconsistent www/non-www Usage",
                description=f"Found {len(inconsistent_links)} internal links using different www format than current page.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.CRAWLABILITY,
                impact="Inconsistent www usage can dilute link equity and cause crawl inefficiency.",
                fix_steps=[
                    "Choose either www or non-www as your preferred format",
                    "Update all internal links to use the preferred format",
                    "Set up 301 redirect from non-preferred to preferred",
                    "Set preferred domain in Google Search Console"
                ],
                expected_outcome="Consistent URL format across all internal links.",
                validation_steps=[
                    "Check that all internal links use same www format",
                    "Verify redirect is in place for alternate format"
                ],
                current_value=f"{'www' if current_has_www else 'non-www'} on page, {len(inconsistent_links)} inconsistent links",
                affected_elements=inconsistent_links[:5],
                difficulty="medium",
                priority_score=40
            ))

    def _check_trailing_slash_consistency(self) -> None:
        """Check for trailing slash consistency in internal links."""
        current_has_trailing = self.parsed_url.path.endswith('/') or self.parsed_url.path == ''

        all_links = self.soup.find_all('a', href=True)
        inconsistent_links = []

        current_domain = self.parsed_url.netloc.lower()

        for link in all_links:
            href = link.get('href', '')

            # Handle relative and absolute URLs
            if href.startswith('/') and not href.startswith('//'):
                # Relative path
                link_path = urlparse(href).path
                if link_path and not link_path.endswith('/') and '.' not in link_path.split('/')[-1]:
                    # Path without trailing slash and not a file
                    if current_has_trailing:
                        inconsistent_links.append(href[:80])
            elif href.startswith(('http://', 'https://')):
                link_parsed = urlparse(href)
                if link_parsed.netloc.lower() == current_domain:
                    path = link_parsed.path
                    # Skip if path has file extension
                    if path and '.' not in path.split('/')[-1]:
                        link_has_trailing = path.endswith('/') or path == ''
                        if link_has_trailing != current_has_trailing:
                            inconsistent_links.append(href[:80])

        if len(inconsistent_links) > 5:
            self.result.data['trailing_slash_consistency'] = {
                'inconsistent_count': len(inconsistent_links)
            }

            self.result.add_issue(SEOIssue(
                title="Inconsistent Trailing Slash Usage",
                description=f"Found {len(inconsistent_links)} internal links with different trailing slash format.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.CRAWLABILITY,
                impact="Inconsistent trailing slashes can create duplicate URL versions.",
                fix_steps=[
                    "Choose a trailing slash convention (with or without)",
                    "Update all internal links to match",
                    "Set up 301 redirects from non-preferred to preferred",
                    "Configure your web server to enforce consistency"
                ],
                expected_outcome="Consistent URL format, no duplicate versions.",
                validation_steps=[
                    "Check internal links for consistent trailing slashes",
                    "Verify redirects work for alternate format"
                ],
                current_value=f"{'with' if current_has_trailing else 'without'} trailing slash on page",
                affected_elements=inconsistent_links[:5],
                difficulty="medium",
                priority_score=35
            ))

    def _check_duplicate_meta_tags(self) -> None:
        """Check for duplicate meta tags."""
        # Check for multiple titles
        titles = self.soup.find_all('title')
        if len(titles) > 1:
            self.result.add_issue(SEOIssue(
                title="Multiple Title Tags",
                description=f"Found {len(titles)} title tags. Only one should exist.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PAGE_CONTENT,
                impact="Multiple title tags confuse search engines. Only the first may be used.",
                fix_steps=[
                    "Remove duplicate title tags",
                    "Keep only one title tag in the <head> section"
                ],
                expected_outcome="Single, clear title tag.",
                validation_steps=[
                    "Search page source for <title>",
                    "Verify only one exists"
                ],
                current_value=f"{len(titles)} title tags",
                recommended_value="Exactly 1 title tag",
                difficulty="easy",
                priority_score=70
            ))

        # Check for multiple meta descriptions
        meta_descriptions = self.soup.find_all('meta', attrs={'name': re.compile(r'^description$', re.I)})
        if len(meta_descriptions) > 1:
            self.result.add_issue(SEOIssue(
                title="Multiple Meta Descriptions",
                description=f"Found {len(meta_descriptions)} meta description tags.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PAGE_CONTENT,
                impact="Multiple meta descriptions may cause inconsistent snippets in search results.",
                fix_steps=[
                    "Remove duplicate meta description tags",
                    "Keep only one meta description"
                ],
                expected_outcome="Single, optimized meta description.",
                validation_steps=[
                    "Search page source for meta description",
                    "Verify only one exists"
                ],
                current_value=f"{len(meta_descriptions)} meta descriptions",
                recommended_value="Exactly 1 meta description",
                difficulty="easy",
                priority_score=60
            ))

        # Check for multiple canonical tags
        canonicals = self.soup.find_all('link', attrs={'rel': 'canonical'})
        if len(canonicals) > 1:
            self.result.add_issue(SEOIssue(
                title="Multiple Canonical Tags",
                description=f"Found {len(canonicals)} canonical tags. Only one should exist.",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.CRAWLABILITY,
                impact="Multiple canonicals send conflicting signals. Search engines may ignore all of them.",
                fix_steps=[
                    "Remove all but one canonical tag",
                    "Ensure the remaining one points to the correct URL"
                ],
                expected_outcome="Single, correct canonical tag.",
                validation_steps=[
                    "Search page source for rel='canonical'",
                    "Verify only one exists with correct URL"
                ],
                current_value=f"{len(canonicals)} canonical tags",
                recommended_value="Exactly 1 canonical tag",
                difficulty="easy",
                priority_score=85
            ))

        self.result.data['duplicate_meta'] = {
            'title_count': len(titles),
            'meta_desc_count': len(meta_descriptions),
            'canonical_count': len(canonicals)
        }
