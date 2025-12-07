"""
SEO Audit Agent - Main agent class that orchestrates the SEO audit.
"""

import time
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse

from .utils import normalize_url, is_valid_url
from .analyzers import (
    CrawlabilityAnalyzer,
    PageAnalyzer,
    PerformanceAnalyzer,
    SecurityAnalyzer,
    StructuredDataAnalyzer,
    LinkAnalyzer,
    MobileAnalyzer,
    DuplicateContentAnalyzer,
)
from .report import AuditReport, ReportGenerator


class SEOAuditAgent:
    """
    SEO Audit Agent that performs comprehensive technical SEO analysis.

    This agent acts as a Senior Technical SEO Specialist, analyzing websites
    for critical SEO issues and providing prioritized, actionable recommendations.
    """

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (compatible; SEOAuditAgent/1.0; "
        "+https://github.com/seo-audit-agent)"
    )

    def __init__(
        self,
        timeout: int = 30,
        user_agent: Optional[str] = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
    ):
        """
        Initialize the SEO Audit Agent.

        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
            verify_ssl: Whether to verify SSL certificates
            follow_redirects: Whether to follow redirects
        """
        self.timeout = timeout
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.verify_ssl = verify_ssl
        self.follow_redirects = follow_redirects

        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })

        # Report generator
        self.report_generator = ReportGenerator()

    def fetch_page(self, url: str) -> Dict[str, Any]:
        """
        Fetch a web page and return its content and metadata.

        Args:
            url: The URL to fetch

        Returns:
            Dictionary with page content, headers, status code, and timing
        """
        start_time = time.time()

        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                verify=self.verify_ssl,
                allow_redirects=self.follow_redirects,
            )

            response_time = (time.time() - start_time) * 1000  # Convert to ms

            return {
                'success': True,
                'url': response.url,
                'original_url': url,
                'status_code': response.status_code,
                'content': response.text,
                'headers': dict(response.headers),
                'response_time': response_time,
                'content_length': len(response.content),
                'redirects': [r.url for r in response.history] if response.history else [],
                'is_https': response.url.startswith('https://'),
            }

        except requests.exceptions.SSLError as e:
            return {
                'success': False,
                'error': f'SSL Error: {str(e)}',
                'error_type': 'ssl_error',
                'url': url,
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'success': False,
                'error': f'Connection Error: {str(e)}',
                'error_type': 'connection_error',
                'url': url,
            }
        except requests.exceptions.Timeout as e:
            return {
                'success': False,
                'error': f'Timeout Error: {str(e)}',
                'error_type': 'timeout',
                'url': url,
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request Error: {str(e)}',
                'error_type': 'request_error',
                'url': url,
            }

    def audit(
        self,
        url: str,
        include_crawlability: bool = True,
        include_page_analysis: bool = True,
        include_performance: bool = True,
        include_security: bool = True,
        include_structured_data: bool = True,
        include_links: bool = True,
        include_mobile: bool = True,
        include_duplicate_content: bool = True,
    ) -> AuditReport:
        """
        Perform a complete SEO audit on a URL.

        Args:
            url: The URL to audit
            include_*: Flags to include/exclude specific analysis modules

        Returns:
            AuditReport containing all findings
        """
        # Normalize URL
        url = normalize_url(url)

        if not is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")

        # Create report
        report = AuditReport(
            url=url,
            audit_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Fetch the page
        page_data = self.fetch_page(url)

        if not page_data['success']:
            report.summary_data['fetch_error'] = page_data['error']
            return report

        # Store page metadata
        report.summary_data['status_code'] = page_data['status_code']
        report.summary_data['response_time'] = page_data['response_time']
        report.summary_data['is_https'] = page_data['is_https']
        report.summary_data['redirects'] = page_data['redirects']

        # Get common parameters
        final_url = page_data['url']
        html_content = page_data['content']
        headers = page_data['headers']

        # Run analyzers
        if include_crawlability:
            analyzer = CrawlabilityAnalyzer(
                url=final_url,
                html_content=html_content,
                response_headers=headers,
                session=self.session,
            )
            result = analyzer.analyze()
            report.add_result(result)

        if include_page_analysis:
            analyzer = PageAnalyzer(
                url=final_url,
                html_content=html_content,
                response_headers=headers,
            )
            result = analyzer.analyze()
            report.add_result(result)

        if include_performance:
            analyzer = PerformanceAnalyzer(
                url=final_url,
                html_content=html_content,
                response_headers=headers,
                response_time=page_data['response_time'],
                page_size=page_data['content_length'],
            )
            result = analyzer.analyze()
            report.add_result(result)

        if include_security:
            analyzer = SecurityAnalyzer(
                url=final_url,
                html_content=html_content,
                response_headers=headers,
                is_https=page_data['is_https'],
            )
            result = analyzer.analyze()
            report.add_result(result)

        if include_structured_data:
            analyzer = StructuredDataAnalyzer(
                url=final_url,
                html_content=html_content,
                response_headers=headers,
            )
            result = analyzer.analyze()
            report.add_result(result)

        if include_links:
            analyzer = LinkAnalyzer(
                url=final_url,
                html_content=html_content,
                response_headers=headers,
            )
            result = analyzer.analyze()
            report.add_result(result)

        if include_mobile:
            analyzer = MobileAnalyzer(
                url=final_url,
                html_content=html_content,
                response_headers=headers,
            )
            result = analyzer.analyze()
            report.add_result(result)

        if include_duplicate_content:
            analyzer = DuplicateContentAnalyzer(
                url=final_url,
                html_content=html_content,
                response_headers=headers,
            )
            result = analyzer.analyze()
            report.add_result(result)

        # Sort issues by priority
        report.sort_issues_by_priority()

        return report

    def generate_report(
        self,
        report: AuditReport,
        format: str = 'console',
        use_colors: bool = True,
    ) -> str:
        """
        Generate a formatted report.

        Args:
            report: The audit report to format
            format: Output format ('console', 'json', 'markdown')
            use_colors: Whether to use colors in console output

        Returns:
            Formatted report string
        """
        self.report_generator.use_colors = use_colors

        if format == 'json':
            return self.report_generator.generate_json_report(report)
        elif format == 'markdown':
            return self.report_generator.generate_markdown_report(report)
        else:
            return self.report_generator.generate_console_report(report)

    def ask_goal_question(self) -> str:
        """
        Generate the goal clarification question.

        Returns:
            The question to ask the user about their SEO goals
        """
        return """
Before we dive into the audit findings, I'd like to understand your primary goal.
What's driving your SEO audit today?

  1. Traffic Growth - Looking to increase organic search traffic
  2. Technical Fixes - Addressing known technical SEO issues
  3. Migration Prep - Preparing for a site migration or redesign
  4. Performance - Improving Core Web Vitals and page speed
  5. General Audit - Comprehensive review of current SEO health

Enter the number or describe your goal:"""

    def get_goal_recommendations(self, goal: str) -> str:
        """
        Get additional recommendations based on the user's goal.

        Args:
            goal: The user's stated goal

        Returns:
            Goal-specific recommendations
        """
        goal_lower = goal.lower()

        if '1' in goal or 'traffic' in goal_lower or 'growth' in goal_lower:
            return """
GOAL-SPECIFIC RECOMMENDATIONS FOR TRAFFIC GROWTH:

Focus Areas:
1. Prioritize fixing any indexability issues (canonical, noindex, robots)
2. Ensure title tags and meta descriptions are compelling and keyword-optimized
3. Check that your main content pages have proper H1 tags with target keywords
4. Add structured data to enable rich snippets and improve CTR
5. Build internal links to your most important pages

Quick Wins:
- Fix any critical crawlability issues immediately
- Optimize meta descriptions for higher click-through rates
- Add FAQ schema to capture featured snippets
- Improve internal linking to distribute page authority
"""

        elif '2' in goal or 'technical' in goal_lower or 'fix' in goal_lower:
            return """
GOAL-SPECIFIC RECOMMENDATIONS FOR TECHNICAL FIXES:

Focus Areas:
1. Address critical issues first (noindex, HTTPS, broken links)
2. Fix any crawlability blockers in robots.txt
3. Ensure proper canonical implementation
4. Resolve mixed content warnings
5. Implement missing security headers

Quick Wins:
- Add missing XML sitemap or fix existing one
- Implement HSTS header if using HTTPS
- Fix any empty or duplicate title tags
- Add viewport meta tag for mobile compatibility
"""

        elif '3' in goal or 'migration' in goal_lower:
            return """
GOAL-SPECIFIC RECOMMENDATIONS FOR MIGRATION PREP:

Focus Areas:
1. Document all current URLs and their SEO elements (titles, canonicals, etc.)
2. Create comprehensive redirect mapping plan
3. Preserve all structured data implementations
4. Maintain internal link architecture
5. Keep URL structure as similar as possible

Pre-Migration Checklist:
- Export current sitemap for reference
- Document all current rankings and traffic
- Plan 301 redirects for all changing URLs
- Test new site in staging before launch
- Prepare Search Console for domain change if needed
"""

        elif '4' in goal or 'performance' in goal_lower or 'speed' in goal_lower or 'vital' in goal_lower:
            return """
GOAL-SPECIFIC RECOMMENDATIONS FOR PERFORMANCE:

Focus Areas:
1. Reduce server response time (TTFB) below 200ms
2. Optimize Largest Contentful Paint (LCP) - target under 2.5s
3. Minimize Cumulative Layout Shift (CLS) - target under 0.1
4. Improve First Input Delay (FID) - target under 100ms

Quick Wins:
- Enable text compression (gzip/brotli)
- Add width/height to images to prevent layout shifts
- Implement lazy loading for below-fold images
- Use preconnect for critical third-party domains
- Add async/defer to non-critical scripts
"""

        else:
            return """
GENERAL SEO AUDIT RECOMMENDATIONS:

Priority Order:
1. Fix all Critical issues first - these have immediate impact
2. Address Important issues within 2-4 weeks
3. Implement Recommended enhancements as time permits

Ongoing Best Practices:
- Monitor Core Web Vitals in Search Console
- Regularly check for crawl errors
- Keep content fresh and up-to-date
- Build quality internal links
- Track rankings for key terms
"""


def create_agent(**kwargs) -> SEOAuditAgent:
    """
    Factory function to create an SEO Audit Agent.

    Args:
        **kwargs: Arguments passed to SEOAuditAgent constructor

    Returns:
        Configured SEOAuditAgent instance
    """
    return SEOAuditAgent(**kwargs)
