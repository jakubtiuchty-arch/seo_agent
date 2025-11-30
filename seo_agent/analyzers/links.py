"""
Link Analyzer - Checks internal linking, external links, and anchor text.
"""

import re
from typing import Dict, List, Set, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import Counter

from .base import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity, IssueCategory
from ..utils import get_domain, is_same_domain, make_absolute_url


class LinkAnalyzer(BaseAnalyzer):
    """Analyzer for internal and external link structure."""

    name = "links"

    def __init__(self, url: str, html_content: str, response_headers: Dict[str, str]):
        super().__init__(url, html_content, response_headers)
        self.soup = BeautifulSoup(html_content, 'lxml')
        self.parsed_url = urlparse(url)
        self.base_domain = get_domain(url)

    def analyze(self) -> AnalysisResult:
        """Perform link analysis."""
        try:
            self._analyze_all_links()
            self._check_internal_linking()
            self._check_anchor_text_distribution()
            self._check_broken_link_patterns()
            self._check_link_depth()
            self._check_orphan_indicators()
            self.result.success = True
        except Exception as e:
            self.result.success = False
            self.result.error = str(e)

        return self.result

    def _analyze_all_links(self) -> None:
        """Analyze all links on the page."""
        all_links = self.soup.find_all('a', href=True)

        internal_links = []
        external_links = []
        nofollow_links = []
        empty_href_links = []
        javascript_links = []
        hash_only_links = []

        for link in all_links:
            href = link.get('href', '').strip()
            rel = link.get('rel', [])
            if isinstance(rel, str):
                rel = rel.split()

            # Categorize link
            if not href:
                empty_href_links.append(link)
            elif href.startswith('#'):
                hash_only_links.append(href)
            elif href.startswith('javascript:'):
                javascript_links.append(href[:50])
            elif href.startswith('mailto:') or href.startswith('tel:'):
                pass  # Skip contact links
            else:
                # Make absolute URL
                absolute_url = make_absolute_url(self.url, href)
                link_domain = get_domain(absolute_url)

                if link_domain == self.base_domain:
                    internal_links.append({
                        'url': absolute_url,
                        'anchor': link.get_text(strip=True)[:100],
                        'nofollow': 'nofollow' in rel
                    })
                else:
                    external_links.append({
                        'url': absolute_url[:200],
                        'anchor': link.get_text(strip=True)[:100],
                        'nofollow': 'nofollow' in rel,
                        'target': link.get('target', '')
                    })

            if 'nofollow' in rel:
                nofollow_links.append(href[:100])

        self.result.data['links'] = {
            'total': len(all_links),
            'internal_count': len(internal_links),
            'external_count': len(external_links),
            'nofollow_count': len(nofollow_links),
            'empty_href_count': len(empty_href_links),
            'javascript_count': len(javascript_links),
            'hash_only_count': len(hash_only_links),
            'internal_links': internal_links[:50],  # Sample
            'external_links': external_links[:30],  # Sample
        }

    def _check_internal_linking(self) -> None:
        """Check internal linking quality."""
        links_data = self.result.data.get('links', {})
        internal_count = links_data.get('internal_count', 0)
        total_links = links_data.get('total', 0)

        # Check for very few internal links
        if internal_count < 3:
            self.result.add_issue(SEOIssue(
                title="Insufficient Internal Links",
                description=f"This page has only {internal_count} internal links.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.LINKS,
                impact="Internal links help distribute page authority and help users/crawlers discover content. Too few limits SEO potential.",
                fix_steps=[
                    "Add relevant internal links to other pages on your site",
                    "Link to related content, categories, or important pages",
                    "Use descriptive anchor text that includes keywords",
                    "Consider adding a 'Related Posts' or 'See Also' section",
                    "Ensure navigation includes key pages"
                ],
                expected_outcome="Better page authority distribution and improved crawlability.",
                validation_steps=[
                    "Count internal links on the page",
                    "Verify links are crawlable (not JavaScript-only)",
                    "Check that anchor text is descriptive"
                ],
                current_value=f"{internal_count} internal links",
                recommended_value="At least 3-5 internal links per page",
                difficulty="easy",
                priority_score=60
            ))

        # Check for excessive links
        if total_links > 200:
            self.result.add_issue(SEOIssue(
                title="Excessive Number of Links",
                description=f"This page has {total_links} links, which is quite high.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.LINKS,
                impact="Too many links can dilute page authority and may overwhelm users. Google may not follow all links.",
                fix_steps=[
                    "Review if all links are necessary",
                    "Consider pagination or 'load more' for link-heavy pages",
                    "Remove duplicate or redundant links",
                    "Use nofollow for less important links (sparingly)"
                ],
                expected_outcome="More focused link equity distribution.",
                validation_steps=[
                    "Count total links on page",
                    "Review for duplicate or unnecessary links"
                ],
                current_value=f"{total_links} total links",
                recommended_value="Under 200 links recommended",
                difficulty="medium",
                priority_score=30
            ))

        # Check for empty href links
        empty_count = links_data.get('empty_href_count', 0)
        if empty_count > 0:
            self.result.add_issue(SEOIssue(
                title="Links with Empty href Attribute",
                description=f"Found {empty_count} links with empty or missing href values.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.LINKS,
                impact="Empty href links don't pass value and can cause unexpected behavior.",
                fix_steps=[
                    "Add proper URLs to href attributes",
                    "If links are for JavaScript interaction, use button elements instead",
                    "Remove empty anchor tags if not needed"
                ],
                expected_outcome="All links have proper destinations.",
                validation_steps=[
                    "Search HTML for href='' or href='#'",
                    "Verify all anchor tags have valid hrefs"
                ],
                current_value=f"{empty_count} empty href links",
                difficulty="easy",
                priority_score=25
            ))

        # Check for JavaScript-only links
        js_count = links_data.get('javascript_count', 0)
        if js_count > 3:
            self.result.add_issue(SEOIssue(
                title="JavaScript-Based Links Detected",
                description=f"Found {js_count} links using javascript: in href.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.LINKS,
                impact="javascript: links are not crawlable by search engines and don't pass link equity.",
                fix_steps=[
                    "Replace javascript: hrefs with actual URLs",
                    "Use progressive enhancement: real href + JS behavior",
                    "Example: <a href='/page' onclick='handleClick(event)'>",
                    "For non-navigation actions, use <button> instead"
                ],
                expected_outcome="Crawlable links that work without JavaScript.",
                validation_steps=[
                    "Search for 'javascript:' in href attributes",
                    "Test links with JavaScript disabled"
                ],
                current_value=f"{js_count} javascript: links",
                recommended_value="0 (use real URLs)",
                difficulty="medium",
                priority_score=55
            ))

    def _check_anchor_text_distribution(self) -> None:
        """Analyze anchor text quality and distribution."""
        internal_links = self.result.data.get('links', {}).get('internal_links', [])

        if not internal_links:
            return

        anchor_texts = [link['anchor'] for link in internal_links]

        # Check for generic anchor text
        generic_anchors = ['click here', 'read more', 'learn more', 'here', 'link',
                          'this', 'more', 'continue', 'go', 'see more']
        generic_count = sum(1 for anchor in anchor_texts
                          if anchor.lower().strip() in generic_anchors)

        # Check for empty anchor text
        empty_count = sum(1 for anchor in anchor_texts if not anchor.strip())

        # Check for very long anchor text
        long_anchors = [a for a in anchor_texts if len(a) > 100]

        self.result.data['anchor_text'] = {
            'generic_count': generic_count,
            'empty_count': empty_count,
            'long_count': len(long_anchors)
        }

        if generic_count > 3:
            self.result.add_issue(SEOIssue(
                title="Generic Anchor Text Usage",
                description=f"Found {generic_count} links using generic anchor text like 'click here' or 'read more'.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.LINKS,
                impact="Descriptive anchor text helps search engines understand what the linked page is about. Generic text wastes this opportunity.",
                fix_steps=[
                    "Replace generic anchors with descriptive text",
                    "Include relevant keywords in anchor text",
                    "Instead of 'Click here to learn about SEO'",
                    "Use 'Learn about our SEO services'",
                    "Keep anchor text concise but descriptive"
                ],
                expected_outcome="Better keyword signals and improved link value.",
                validation_steps=[
                    "Review anchor text for all internal links",
                    "Ensure anchors describe the linked content"
                ],
                current_value=f"{generic_count} generic anchors",
                recommended_value="Descriptive, keyword-relevant anchors",
                difficulty="easy",
                priority_score=35
            ))

        if empty_count > 2:
            self.result.add_issue(SEOIssue(
                title="Links with No Anchor Text",
                description=f"Found {empty_count} links without any anchor text.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.LINKS,
                impact="Links without anchor text provide no context to search engines and may indicate image-only links without alt text.",
                fix_steps=[
                    "Add descriptive text to links",
                    "For image links, ensure images have alt text",
                    "Example: <a href='...'><img src='...' alt='Description'></a>",
                    "Remove empty links if they're not needed"
                ],
                expected_outcome="All links provide context through text or image alt attributes.",
                validation_steps=[
                    "Find links with no text content",
                    "Check image links for alt text"
                ],
                current_value=f"{empty_count} empty anchor texts",
                difficulty="easy",
                priority_score=50
            ))

    def _check_broken_link_patterns(self) -> None:
        """Check for patterns that might indicate broken links."""
        internal_links = self.result.data.get('links', {}).get('internal_links', [])

        suspicious_patterns = []
        for link in internal_links:
            url = link.get('url', '')
            # Check for obviously broken patterns
            if '/undefined' in url or '/null' in url:
                suspicious_patterns.append(url[:80])
            elif url.endswith('/404') or '/404/' in url:
                suspicious_patterns.append(url[:80])
            elif '{{' in url or '}}' in url:  # Template variables
                suspicious_patterns.append(url[:80])
            elif '${' in url:  # JavaScript template literals
                suspicious_patterns.append(url[:80])

        if suspicious_patterns:
            self.result.add_issue(SEOIssue(
                title="Potentially Broken Link Patterns",
                description=f"Found {len(suspicious_patterns)} links with suspicious URL patterns.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.LINKS,
                impact="Broken links hurt user experience and waste crawl budget. They can also indicate JavaScript errors.",
                fix_steps=[
                    "Review the flagged links for accuracy",
                    "Fix any template variables that weren't properly replaced",
                    "Remove or correct obviously broken links",
                    "Test links to ensure they work"
                ],
                expected_outcome="All links resolve to valid pages.",
                validation_steps=[
                    "Click through suspicious links",
                    "Run a broken link checker on your site",
                    "Check browser console for JavaScript errors"
                ],
                affected_elements=suspicious_patterns[:10],
                difficulty="medium",
                priority_score=65
            ))

    def _check_link_depth(self) -> None:
        """Analyze URL depth patterns in internal links."""
        internal_links = self.result.data.get('links', {}).get('internal_links', [])

        if not internal_links:
            return

        # Count path depths
        depths = []
        for link in internal_links:
            url = link.get('url', '')
            path = urlparse(url).path
            depth = len([p for p in path.split('/') if p])
            depths.append(depth)

        if depths:
            avg_depth = sum(depths) / len(depths)
            max_depth = max(depths)

            self.result.data['link_depth'] = {
                'average': round(avg_depth, 2),
                'maximum': max_depth
            }

            if max_depth > 5:
                self.result.add_issue(SEOIssue(
                    title="Deep URL Structure Detected",
                    description=f"Some internal links point to URLs with {max_depth} directory levels.",
                    severity=IssueSeverity.RECOMMENDED,
                    category=IssueCategory.LINKS,
                    impact="Deep URLs can indicate poor site architecture. Important pages should be accessible within 3-4 clicks.",
                    fix_steps=[
                        "Review your site's URL structure",
                        "Flatten deep hierarchies where possible",
                        "Ensure important pages are no more than 3 clicks from homepage",
                        "Use internal links to connect deep pages"
                    ],
                    expected_outcome="Shallower site architecture with better crawlability.",
                    validation_steps=[
                        "Check URL depth of important pages",
                        "Verify pages are reachable in 3-4 clicks"
                    ],
                    current_value=f"Max depth: {max_depth} levels",
                    recommended_value="Keep important pages within 3-4 levels",
                    difficulty="hard",
                    priority_score=30
                ))

    def _check_orphan_indicators(self) -> None:
        """Check for indicators that this might be an orphan page."""
        # This is a basic check - full orphan detection requires crawling
        internal_links = self.result.data.get('links', {}).get('internal_links', [])

        # Check if page links to itself (self-referencing)
        self_links = [link for link in internal_links
                     if urlparse(link['url']).path == self.parsed_url.path]

        # Check for navigation elements
        nav = self.soup.find('nav')
        header_links = self.soup.find('header')
        footer_links = self.soup.find('footer')

        has_nav_elements = nav is not None or header_links is not None or footer_links is not None

        self.result.data['navigation'] = {
            'has_nav': nav is not None,
            'has_header': header_links is not None,
            'has_footer': footer_links is not None,
            'self_links': len(self_links)
        }

        # Very basic check - page with no navigation might be orphaned
        if not has_nav_elements and len(internal_links) < 5:
            self.result.add_issue(SEOIssue(
                title="Potential Orphan Page Warning",
                description="This page has minimal navigation elements and few internal links.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.LINKS,
                impact="Pages without proper navigation or internal links may be hard to find for users and search engines.",
                fix_steps=[
                    "Ensure the page is linked from your main navigation",
                    "Add the page to relevant category or parent pages",
                    "Include related internal links in the content",
                    "Verify the page appears in your sitemap"
                ],
                expected_outcome="Page is properly integrated into site structure.",
                validation_steps=[
                    "Search for links to this page from other pages",
                    "Verify page is in sitemap",
                    "Check navigation includes this page or its parent"
                ],
                difficulty="medium",
                priority_score=40
            ))
