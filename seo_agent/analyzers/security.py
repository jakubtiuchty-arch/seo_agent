"""
Security Analyzer - Checks HTTPS, security headers, and SSL configuration.
"""

from typing import Dict, List, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from .base import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity, IssueCategory


class SecurityAnalyzer(BaseAnalyzer):
    """Analyzer for security-related SEO issues."""

    name = "security"

    # Important security headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': {
            'severity': IssueSeverity.IMPORTANT,
            'impact': 'HSTS prevents protocol downgrade attacks and cookie hijacking.',
            'recommended': 'max-age=31536000; includeSubDomains; preload'
        },
        'X-Content-Type-Options': {
            'severity': IssueSeverity.RECOMMENDED,
            'impact': 'Prevents MIME type sniffing attacks.',
            'recommended': 'nosniff'
        },
        'X-Frame-Options': {
            'severity': IssueSeverity.RECOMMENDED,
            'impact': 'Prevents clickjacking attacks by controlling iframe embedding.',
            'recommended': 'SAMEORIGIN'
        },
        'Content-Security-Policy': {
            'severity': IssueSeverity.RECOMMENDED,
            'impact': 'CSP prevents XSS and data injection attacks.',
            'recommended': "default-src 'self'"
        },
        'Referrer-Policy': {
            'severity': IssueSeverity.RECOMMENDED,
            'impact': 'Controls how much referrer information is shared.',
            'recommended': 'strict-origin-when-cross-origin'
        },
        'Permissions-Policy': {
            'severity': IssueSeverity.RECOMMENDED,
            'impact': 'Controls browser features and APIs available to the page.',
            'recommended': 'geolocation=(), microphone=(), camera=()'
        }
    }

    def __init__(self, url: str, html_content: str, response_headers: Dict[str, str],
                 is_https: bool = None, ssl_info: Optional[Dict] = None):
        super().__init__(url, html_content, response_headers)
        self.soup = BeautifulSoup(html_content, 'lxml')
        self.parsed_url = urlparse(url)
        self.is_https = is_https if is_https is not None else self.parsed_url.scheme == 'https'
        self.ssl_info = ssl_info or {}

    def analyze(self) -> AnalysisResult:
        """Perform security analysis."""
        try:
            self._check_https()
            self._check_security_headers()
            self._check_mixed_content()
            self._check_unsafe_links()
            self._check_form_security()
            self.result.success = True
        except Exception as e:
            self.result.success = False
            self.result.error = str(e)

        return self.result

    def _check_https(self) -> None:
        """Check HTTPS implementation."""
        self.result.data['https'] = {
            'enabled': self.is_https,
            'scheme': self.parsed_url.scheme
        }

        if not self.is_https:
            self.result.add_issue(SEOIssue(
                title="Site Not Using HTTPS",
                description="This website is served over HTTP instead of HTTPS.",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.SECURITY,
                impact="HTTPS is a Google ranking factor. Sites without HTTPS are marked as 'Not Secure' in browsers, destroying user trust. Data is transmitted unencrypted.",
                fix_steps=[
                    "Obtain an SSL/TLS certificate (free from Let's Encrypt)",
                    "Install the certificate on your web server",
                    "Configure your server to serve content over HTTPS",
                    "Set up 301 redirects from HTTP to HTTPS",
                    "Update all internal links to use HTTPS",
                    "Update sitemap and Google Search Console"
                ],
                expected_outcome="Secure connection, improved rankings, 'Secure' badge in browser, protected user data.",
                validation_steps=[
                    "Visit your site with https:// prefix",
                    "Check for padlock icon in browser address bar",
                    "Verify HTTP URLs redirect to HTTPS",
                    "Test with SSL Labs (ssllabs.com/ssltest)"
                ],
                current_value="HTTP (insecure)",
                recommended_value="HTTPS",
                difficulty="medium",
                priority_score=100
            ))

    def _check_security_headers(self) -> None:
        """Check for important security headers."""
        present_headers = {}
        missing_headers = []

        for header, config in self.SECURITY_HEADERS.items():
            # Check various header name formats
            header_value = (
                self.response_headers.get(header) or
                self.response_headers.get(header.lower()) or
                self.response_headers.get(header.replace('-', '_'))
            )

            if header_value:
                present_headers[header] = header_value
            else:
                missing_headers.append(header)

        self.result.data['security_headers'] = {
            'present': present_headers,
            'missing': missing_headers
        }

        # Check for critical missing headers
        if 'Strict-Transport-Security' in missing_headers and self.is_https:
            self.result.add_issue(SEOIssue(
                title="Missing HSTS Header",
                description="Strict-Transport-Security (HSTS) header is not set.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.SECURITY,
                impact="Without HSTS, users could be vulnerable to SSL stripping attacks. Browsers won't remember to always use HTTPS.",
                fix_steps=[
                    "Add HSTS header to your server configuration",
                    "Apache: Header always set Strict-Transport-Security 'max-age=31536000; includeSubDomains'",
                    "Nginx: add_header Strict-Transport-Security 'max-age=31536000; includeSubDomains' always;",
                    "Start with a short max-age (300) for testing",
                    "Gradually increase to 31536000 (1 year)",
                    "Consider HSTS preload for maximum security"
                ],
                expected_outcome="Browsers will always use HTTPS, preventing downgrade attacks.",
                validation_steps=[
                    "Check response headers for Strict-Transport-Security",
                    "Use securityheaders.com to verify",
                    "Test with browser DevTools Network tab"
                ],
                recommended_value="max-age=31536000; includeSubDomains",
                difficulty="easy",
                priority_score=70
            ))

        # Report other missing security headers
        other_missing = [h for h in missing_headers if h != 'Strict-Transport-Security']
        if len(other_missing) >= 3:
            self.result.add_issue(SEOIssue(
                title="Multiple Security Headers Missing",
                description=f"Missing {len(other_missing)} recommended security headers: {', '.join(other_missing[:4])}",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.SECURITY,
                impact="Missing security headers can leave your site vulnerable to various attacks (XSS, clickjacking, etc.).",
                fix_steps=[
                    "Add the following headers to your server configuration:",
                    "  X-Content-Type-Options: nosniff",
                    "  X-Frame-Options: SAMEORIGIN",
                    "  Referrer-Policy: strict-origin-when-cross-origin",
                    "Consider implementing Content-Security-Policy (requires careful configuration)",
                    "Use securityheaders.com to test your implementation"
                ],
                expected_outcome="Better protection against common web vulnerabilities.",
                validation_steps=[
                    "Check response headers in browser DevTools",
                    "Use securityheaders.com for comprehensive check",
                    "Run security scanner to verify protections"
                ],
                current_value=f"Missing: {', '.join(other_missing)}",
                affected_elements=other_missing,
                difficulty="medium",
                priority_score=40
            ))

    def _check_mixed_content(self) -> None:
        """Check for mixed content (HTTP resources on HTTPS page)."""
        if not self.is_https:
            return

        mixed_content = {
            'scripts': [],
            'stylesheets': [],
            'images': [],
            'iframes': [],
            'other': []
        }

        # Check scripts
        for script in self.soup.find_all('script', src=True):
            src = script.get('src', '')
            if src.startswith('http://'):
                mixed_content['scripts'].append(src[:80])

        # Check stylesheets
        for link in self.soup.find_all('link', attrs={'rel': 'stylesheet'}):
            href = link.get('href', '')
            if href.startswith('http://'):
                mixed_content['stylesheets'].append(href[:80])

        # Check images
        for img in self.soup.find_all('img'):
            src = img.get('src', img.get('data-src', ''))
            if src.startswith('http://'):
                mixed_content['images'].append(src[:80])

        # Check iframes
        for iframe in self.soup.find_all('iframe'):
            src = iframe.get('src', '')
            if src.startswith('http://'):
                mixed_content['iframes'].append(src[:80])

        # Check forms
        for form in self.soup.find_all('form'):
            action = form.get('action', '')
            if action.startswith('http://'):
                mixed_content['other'].append(f"Form: {action[:80]}")

        total_mixed = sum(len(v) for v in mixed_content.values())

        self.result.data['mixed_content'] = {
            'total': total_mixed,
            'breakdown': {k: len(v) for k, v in mixed_content.items()}
        }

        if total_mixed > 0:
            all_mixed = []
            for category, items in mixed_content.items():
                all_mixed.extend([f"{category}: {item}" for item in items[:3]])

            severity = IssueSeverity.CRITICAL if mixed_content['scripts'] or mixed_content['stylesheets'] else IssueSeverity.IMPORTANT

            self.result.add_issue(SEOIssue(
                title="Mixed Content Detected",
                description=f"Found {total_mixed} HTTP resources on this HTTPS page.",
                severity=severity,
                category=IssueCategory.SECURITY,
                impact="Mixed content can be blocked by browsers, breaking functionality. Active mixed content (scripts, styles) is a security risk.",
                fix_steps=[
                    "Update all resource URLs to use HTTPS or protocol-relative URLs",
                    "Change http:// to https:// or //",
                    "For external resources, verify HTTPS is available",
                    "If third-party doesn't support HTTPS, host the resource yourself",
                    "Use Content-Security-Policy to report mixed content"
                ],
                expected_outcome="All resources load securely, no browser warnings, full site functionality.",
                validation_steps=[
                    "Check browser console for mixed content warnings",
                    "Use browser DevTools Network tab to find HTTP requests",
                    "Run 'whynopadlock.com' to check for mixed content"
                ],
                current_value=f"{total_mixed} HTTP resources",
                recommended_value="0 (all HTTPS)",
                affected_elements=all_mixed[:10],
                difficulty="medium",
                priority_score=90 if severity == IssueSeverity.CRITICAL else 70
            ))

    def _check_unsafe_links(self) -> None:
        """Check for unsafe external link handling."""
        external_links = []
        unsafe_links = []

        current_domain = self.parsed_url.netloc

        for link in self.soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('http'):
                link_domain = urlparse(href).netloc
                if link_domain and link_domain != current_domain:
                    external_links.append(href)
                    # Check for target="_blank" without rel="noopener"
                    if link.get('target') == '_blank':
                        rel = link.get('rel', [])
                        if isinstance(rel, str):
                            rel = rel.split()
                        if 'noopener' not in rel and 'noreferrer' not in rel:
                            unsafe_links.append(href[:80])

        self.result.data['external_links'] = {
            'total': len(external_links),
            'unsafe_blank_targets': len(unsafe_links)
        }

        if unsafe_links:
            self.result.add_issue(SEOIssue(
                title="Unsafe target='_blank' Links",
                description=f"Found {len(unsafe_links)} external links with target='_blank' but no rel='noopener'.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.SECURITY,
                impact="Links with target='_blank' without rel='noopener' can expose your site to tabnabbing attacks.",
                fix_steps=[
                    "Add rel='noopener noreferrer' to all external target='_blank' links",
                    "Example: <a href='...' target='_blank' rel='noopener noreferrer'>",
                    "Modern browsers handle this automatically, but explicit is safer",
                    "Consider if target='_blank' is even needed"
                ],
                expected_outcome="Protection against reverse tabnabbing security vulnerability.",
                validation_steps=[
                    "Search HTML for target='_blank' links",
                    "Verify each has rel='noopener' or rel='noreferrer'",
                    "Use ESLint or linter rules to catch this automatically"
                ],
                current_value=f"{len(unsafe_links)} unsafe links",
                recommended_value="All target='_blank' links should have rel='noopener'",
                affected_elements=unsafe_links[:10],
                difficulty="easy",
                priority_score=30
            ))

    def _check_form_security(self) -> None:
        """Check form security implementation."""
        forms = self.soup.find_all('form')

        insecure_forms = []
        password_forms_without_autocomplete = []

        for form in forms:
            action = form.get('action', '')

            # Check for HTTP form actions on HTTPS pages
            if self.is_https and action.startswith('http://'):
                insecure_forms.append(action[:80])

            # Check password fields
            password_fields = form.find_all('input', attrs={'type': 'password'})
            if password_fields:
                for field in password_fields:
                    if field.get('autocomplete') != 'current-password' and field.get('autocomplete') != 'new-password':
                        password_forms_without_autocomplete.append(action[:80] if action else 'inline form')

        self.result.data['forms'] = {
            'total': len(forms),
            'insecure_actions': len(insecure_forms),
            'password_autocomplete_missing': len(password_forms_without_autocomplete)
        }

        if insecure_forms:
            self.result.add_issue(SEOIssue(
                title="Forms Submitting to HTTP URLs",
                description=f"Found {len(insecure_forms)} forms submitting data to insecure HTTP URLs.",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.SECURITY,
                impact="Form data submitted over HTTP is unencrypted and can be intercepted. Major security and trust issue.",
                fix_steps=[
                    "Update form action URLs to use HTTPS",
                    "If action is empty, ensure page is served over HTTPS",
                    "Verify the target server supports HTTPS",
                    "Test form submission after changes"
                ],
                expected_outcome="All form submissions encrypted via HTTPS.",
                validation_steps=[
                    "Check all form action attributes",
                    "Test form submission and verify HTTPS in DevTools"
                ],
                affected_elements=insecure_forms,
                difficulty="easy",
                priority_score=95
            ))
