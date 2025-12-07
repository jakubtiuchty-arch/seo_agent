"""
Mobile Analyzer - Checks mobile responsiveness and optimization.
"""

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

from .base import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity, IssueCategory


class MobileAnalyzer(BaseAnalyzer):
    """Analyzer for mobile responsiveness and optimization."""

    name = "mobile"

    def __init__(self, url: str, html_content: str, response_headers: Dict[str, str]):
        super().__init__(url, html_content, response_headers)
        self.soup = BeautifulSoup(html_content, 'lxml')

    def analyze(self) -> AnalysisResult:
        """Perform mobile optimization analysis."""
        try:
            self._check_viewport_meta()
            self._check_tap_targets()
            self._check_font_sizes()
            self._check_horizontal_scrolling()
            self._check_mobile_friendly_elements()
            self._check_touch_icons()
            self._check_mobile_redirects()
            self.result.success = True
        except Exception as e:
            self.result.success = False
            self.result.error = str(e)

        return self.result

    def _check_viewport_meta(self) -> None:
        """Check viewport meta tag configuration."""
        viewport = self.soup.find('meta', attrs={'name': 'viewport'})

        if not viewport:
            self.result.data['viewport'] = {'exists': False}
            self.result.add_issue(SEOIssue(
                title="Missing Viewport Meta Tag",
                description="No viewport meta tag found. Essential for mobile responsiveness.",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.MOBILE,
                impact="Without a viewport tag, mobile devices render pages at desktop width, making content unreadable without zooming.",
                fix_steps=[
                    "Add viewport meta tag to your <head> section",
                    "<meta name='viewport' content='width=device-width, initial-scale=1'>",
                    "Avoid maximum-scale=1 as it prevents zooming (accessibility issue)",
                    "Avoid user-scalable=no for the same reason"
                ],
                expected_outcome="Pages render at proper width on mobile devices with appropriate scaling.",
                validation_steps=[
                    "Test page on mobile device or Chrome DevTools device mode",
                    "Run Google's Mobile-Friendly Test",
                    "Verify content is readable without horizontal scrolling"
                ],
                difficulty="easy",
                priority_score=95
            ))
            return

        content = viewport.get('content', '')
        self.result.data['viewport'] = {
            'exists': True,
            'content': content
        }

        # Check for problematic viewport settings
        content_lower = content.lower()

        if 'user-scalable=no' in content_lower or 'user-scalable=0' in content_lower:
            self.result.add_issue(SEOIssue(
                title="Viewport Disables User Zooming",
                description="The viewport meta tag prevents users from zooming (user-scalable=no).",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.MOBILE,
                impact="Disabling zoom is an accessibility violation. Users with vision impairments need to zoom to read content.",
                fix_steps=[
                    "Remove 'user-scalable=no' or 'user-scalable=0' from viewport",
                    "Remove 'maximum-scale=1' if present",
                    "Use: <meta name='viewport' content='width=device-width, initial-scale=1'>"
                ],
                expected_outcome="Users can zoom the page as needed for accessibility.",
                validation_steps=[
                    "Test zooming on mobile device",
                    "Run accessibility audit to verify zoom is allowed"
                ],
                current_value=content,
                recommended_value="width=device-width, initial-scale=1",
                difficulty="easy",
                priority_score=70
            ))

        if 'maximum-scale=1' in content_lower:
            self.result.add_issue(SEOIssue(
                title="Viewport Restricts Maximum Scale",
                description="The viewport sets maximum-scale=1, which may prevent zooming.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.MOBILE,
                impact="Some browsers interpret maximum-scale=1 as disabling zoom, which hurts accessibility.",
                fix_steps=[
                    "Remove 'maximum-scale=1' from viewport",
                    "Allow browser default zoom behavior"
                ],
                expected_outcome="Unrestricted zoom capability for users.",
                validation_steps=[
                    "Verify zoom works on mobile devices"
                ],
                current_value=content,
                difficulty="easy",
                priority_score=40
            ))

    def _check_tap_targets(self) -> None:
        """Check for appropriately sized tap targets."""
        # Find clickable elements
        links = self.soup.find_all('a')
        buttons = self.soup.find_all('button')
        inputs = self.soup.find_all(['input', 'select', 'textarea'])

        # Check for inline style sizing issues
        small_tap_targets = []

        # Check for links/buttons with very small dimensions in inline styles
        for element in links + buttons:
            style = element.get('style', '')
            # Look for small explicit sizes
            width_match = re.search(r'width\s*:\s*(\d+)px', style)
            height_match = re.search(r'height\s*:\s*(\d+)px', style)

            if width_match and int(width_match.group(1)) < 44:
                small_tap_targets.append(f"{element.name}: {element.get_text()[:50]}")
            elif height_match and int(height_match.group(1)) < 44:
                small_tap_targets.append(f"{element.name}: {element.get_text()[:50]}")

        self.result.data['tap_targets'] = {
            'total_clickable': len(links) + len(buttons) + len(inputs),
            'potential_small_targets': len(small_tap_targets)
        }

        # Note: Full tap target analysis requires CSS computation
        # This is a basic heuristic check

    def _check_font_sizes(self) -> None:
        """Check for readable font sizes on mobile."""
        # Find inline styles with small font sizes
        small_font_elements = []

        all_elements = self.soup.find_all(style=True)
        for element in all_elements:
            style = element.get('style', '')
            font_match = re.search(r'font-size\s*:\s*(\d+(?:\.\d+)?)(px|pt|em|rem)', style)
            if font_match:
                size = float(font_match.group(1))
                unit = font_match.group(2)

                # Check for small fonts (less than 12px or 9pt)
                if (unit == 'px' and size < 12) or (unit == 'pt' and size < 9):
                    text = element.get_text()[:50]
                    small_font_elements.append(f"{element.name}: {text}")

        # Check for deprecated font tags
        font_tags = self.soup.find_all('font')
        small_font_tags = []
        for font in font_tags:
            size = font.get('size', '')
            if size and size.isdigit() and int(size) < 2:
                small_font_tags.append(font.get_text()[:50])

        self.result.data['fonts'] = {
            'deprecated_font_tags': len(font_tags),
            'small_inline_fonts': len(small_font_elements)
        }

        if font_tags:
            self.result.add_issue(SEOIssue(
                title="Deprecated <font> Tags Used",
                description=f"Found {len(font_tags)} deprecated <font> tags in HTML.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.MOBILE,
                impact="<font> tags are deprecated HTML. They can cause inconsistent rendering and maintenance issues.",
                fix_steps=[
                    "Replace <font> tags with CSS styling",
                    "Use semantic HTML elements with CSS classes",
                    "Example: Instead of <font size='2'>text</font>",
                    "Use: <span class='small-text'>text</span> with CSS"
                ],
                expected_outcome="Modern, maintainable styling with consistent rendering.",
                validation_steps=[
                    "Search HTML for <font> tags",
                    "Validate HTML with W3C validator"
                ],
                current_value=f"{len(font_tags)} <font> tags",
                difficulty="medium",
                priority_score=25
            ))

        if len(small_font_elements) > 3:
            self.result.add_issue(SEOIssue(
                title="Small Font Sizes Detected",
                description=f"Found {len(small_font_elements)} elements with very small font sizes.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.MOBILE,
                impact="Text smaller than 12px is hard to read on mobile devices without zooming.",
                fix_steps=[
                    "Use a minimum font size of 14-16px for body text",
                    "Ensure text is readable without zooming",
                    "Use relative units (rem, em) instead of px for better scaling",
                    "Set a base font size of at least 16px on the body"
                ],
                expected_outcome="Readable text on all devices without user zooming.",
                validation_steps=[
                    "Test page on mobile device",
                    "Run Lighthouse accessibility audit"
                ],
                current_value=f"{len(small_font_elements)} small font elements",
                recommended_value="Minimum 14-16px for body text",
                difficulty="easy",
                priority_score=35
            ))

    def _check_horizontal_scrolling(self) -> None:
        """Check for elements that might cause horizontal scrolling."""
        # Check for elements with fixed widths larger than common mobile widths
        fixed_width_elements = []

        for element in self.soup.find_all(style=True):
            style = element.get('style', '')
            width_match = re.search(r'width\s*:\s*(\d+)px', style)
            if width_match:
                width = int(width_match.group(1))
                if width > 500:  # Larger than typical mobile width
                    fixed_width_elements.append({
                        'element': element.name,
                        'width': width
                    })

        # Check for tables without responsive handling
        tables = self.soup.find_all('table')
        non_responsive_tables = []
        for table in tables:
            # Check if table has responsive wrapper or overflow handling
            parent = table.parent
            parent_style = parent.get('style', '') if parent else ''
            table_style = table.get('style', '')

            if 'overflow' not in parent_style.lower() and 'overflow' not in table_style.lower():
                non_responsive_tables.append(table)

        self.result.data['horizontal_scroll'] = {
            'fixed_width_elements': len(fixed_width_elements),
            'non_responsive_tables': len(non_responsive_tables)
        }

        if non_responsive_tables:
            self.result.add_issue(SEOIssue(
                title="Tables May Cause Horizontal Scrolling",
                description=f"Found {len(non_responsive_tables)} tables that may overflow on mobile.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.MOBILE,
                impact="Tables that overflow horizontally make content inaccessible on mobile without scrolling.",
                fix_steps=[
                    "Wrap tables in a container with overflow-x: auto",
                    "Consider using responsive table patterns",
                    "For data tables, use CSS: table { width: 100%; max-width: 100%; }",
                    "Consider stacking table data vertically on mobile"
                ],
                expected_outcome="Tables remain usable on mobile devices without breaking layout.",
                validation_steps=[
                    "Test page on mobile device or DevTools",
                    "Verify no horizontal scrollbar appears",
                    "Check table data is accessible on narrow screens"
                ],
                current_value=f"{len(non_responsive_tables)} non-responsive tables",
                difficulty="medium",
                priority_score=55
            ))

        if fixed_width_elements:
            self.result.add_issue(SEOIssue(
                title="Fixed Width Elements May Break Mobile Layout",
                description=f"Found {len(fixed_width_elements)} elements with large fixed widths.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.MOBILE,
                impact="Fixed widths larger than the viewport cause horizontal scrolling on mobile.",
                fix_steps=[
                    "Use percentage widths or max-width instead of fixed widths",
                    "Example: width: 100%; max-width: 600px;",
                    "Use CSS media queries for responsive layouts",
                    "Test layouts at various screen widths"
                ],
                expected_outcome="Responsive layout that adapts to all screen sizes.",
                validation_steps=[
                    "Test page at 320px, 375px, and 414px widths",
                    "Verify no horizontal scrolling occurs"
                ],
                current_value=f"{len(fixed_width_elements)} fixed-width elements",
                difficulty="medium",
                priority_score=40
            ))

    def _check_mobile_friendly_elements(self) -> None:
        """Check for mobile-friendly HTML patterns."""
        # Check for Flash content
        flash_elements = self.soup.find_all(['object', 'embed'])
        flash_content = [el for el in flash_elements
                        if 'flash' in str(el.get('type', '')).lower()
                        or '.swf' in str(el.get('src', '')).lower()
                        or '.swf' in str(el.get('data', '')).lower()]

        if flash_content:
            self.result.add_issue(SEOIssue(
                title="Flash Content Detected",
                description=f"Found {len(flash_content)} Flash objects on the page.",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.MOBILE,
                impact="Flash is not supported on mobile devices and has been deprecated. Content is completely inaccessible.",
                fix_steps=[
                    "Replace Flash content with HTML5 alternatives",
                    "Use HTML5 <video> and <audio> for media",
                    "Use HTML5 Canvas or CSS animations for effects",
                    "Consider modern JavaScript frameworks for interactivity"
                ],
                expected_outcome="Content accessible on all devices including mobile.",
                validation_steps=[
                    "Verify Flash elements are removed",
                    "Test functionality on mobile device"
                ],
                difficulty="hard",
                priority_score=95
            ))

        # Check for app-install interstitials (based on meta tags)
        smart_banners = self.soup.find_all('meta', attrs={'name': 'apple-itunes-app'})

        self.result.data['mobile_elements'] = {
            'flash_content': len(flash_content),
            'smart_app_banners': len(smart_banners)
        }

    def _check_touch_icons(self) -> None:
        """Check for Apple touch icons and favicons."""
        apple_touch_icon = self.soup.find('link', attrs={'rel': re.compile(r'apple-touch-icon', re.I)})
        favicon = self.soup.find('link', attrs={'rel': re.compile(r'icon', re.I)})

        self.result.data['icons'] = {
            'apple_touch_icon': apple_touch_icon is not None,
            'favicon': favicon is not None
        }

        if not apple_touch_icon:
            self.result.add_issue(SEOIssue(
                title="Missing Apple Touch Icon",
                description="No Apple touch icon defined for iOS home screen.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.MOBILE,
                impact="When users add your site to their iOS home screen, it will display a generic icon or screenshot.",
                fix_steps=[
                    "Create a 180x180px PNG icon",
                    "Add to <head>: <link rel='apple-touch-icon' href='/apple-touch-icon.png'>",
                    "Optionally add multiple sizes for different devices",
                    "Use a transparent background or the icon will get rounded corners"
                ],
                expected_outcome="Professional, branded icon when saved to home screen.",
                validation_steps=[
                    "Add site to iOS home screen and verify icon",
                    "Check for apple-touch-icon in page source"
                ],
                difficulty="easy",
                priority_score=20
            ))

        if not favicon:
            self.result.add_issue(SEOIssue(
                title="Missing Favicon",
                description="No favicon defined for browser tabs.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.MOBILE,
                impact="Missing favicon looks unprofessional and makes your site harder to identify in browser tabs.",
                fix_steps=[
                    "Create favicon.ico (32x32 or 16x16)",
                    "Add to <head>: <link rel='icon' href='/favicon.ico'>",
                    "Consider PNG format: <link rel='icon' type='image/png' href='/favicon.png'>",
                    "Add SVG favicon for modern browsers: <link rel='icon' type='image/svg+xml' href='/favicon.svg'>"
                ],
                expected_outcome="Branded icon in browser tabs and bookmarks.",
                validation_steps=[
                    "Check browser tab for favicon",
                    "Verify favicon link in page source"
                ],
                difficulty="easy",
                priority_score=25
            ))

    def _check_mobile_redirects(self) -> None:
        """Check for signs of mobile-specific redirect configuration."""
        # Check for alternate mobile URLs in link tags
        alternate_mobile = self.soup.find('link', attrs={
            'rel': 'alternate',
            'media': re.compile(r'handheld|mobile', re.I)
        })

        # Check for canonical pointing elsewhere
        canonical = self.soup.find('link', attrs={'rel': 'canonical'})

        self.result.data['mobile_config'] = {
            'has_mobile_alternate': alternate_mobile is not None,
            'canonical_url': canonical.get('href') if canonical else None
        }

        # Note: Responsive design is preferred over separate mobile URLs
        if alternate_mobile:
            self.result.add_issue(SEOIssue(
                title="Separate Mobile URL Configuration Detected",
                description="Page uses alternate mobile URL configuration instead of responsive design.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.MOBILE,
                impact="Separate mobile URLs require maintaining two versions and can cause indexing issues. Responsive design is Google's recommended approach.",
                fix_steps=[
                    "Consider migrating to responsive design (single URL for all devices)",
                    "If keeping separate URLs, ensure proper rel='canonical' and rel='alternate' tags",
                    "Verify redirects work correctly for all user agents",
                    "Implement hreflang if serving different languages"
                ],
                expected_outcome="Simplified maintenance with responsive design or proper mobile configuration.",
                validation_steps=[
                    "Test with Google's Mobile-Friendly Test",
                    "Verify both URLs are indexed correctly",
                    "Check mobile usability in Search Console"
                ],
                difficulty="hard",
                priority_score=35
            ))
