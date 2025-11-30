"""
Page Content Analyzer - Checks meta tags, headings, and content quality.
"""

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from collections import Counter

from .base import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity, IssueCategory
from ..utils import extract_text_content, calculate_text_ratio, truncate_text


class PageAnalyzer(BaseAnalyzer):
    """Analyzer for page content, meta tags, and heading structure."""

    name = "page_content"

    # SEO best practice limits
    TITLE_MIN_LENGTH = 30
    TITLE_MAX_LENGTH = 60
    DESCRIPTION_MIN_LENGTH = 70
    DESCRIPTION_MAX_LENGTH = 160
    MIN_CONTENT_LENGTH = 300

    def __init__(self, url: str, html_content: str, response_headers: Dict[str, str]):
        super().__init__(url, html_content, response_headers)
        self.soup = BeautifulSoup(html_content, 'lxml')

    def analyze(self) -> AnalysisResult:
        """Perform page content analysis."""
        try:
            self._check_title_tag()
            self._check_meta_description()
            self._check_heading_hierarchy()
            self._check_image_optimization()
            self._check_content_quality()
            self._check_language_declaration()
            self._check_viewport_meta()
            self._check_open_graph()
            self.result.success = True
        except Exception as e:
            self.result.success = False
            self.result.error = str(e)

        return self.result

    def _check_title_tag(self) -> None:
        """Check title tag for SEO best practices."""
        title_tag = self.soup.find('title')

        if not title_tag:
            self.result.data['title'] = {'exists': False}
            self.result.add_issue(SEOIssue(
                title="Missing Title Tag",
                description="This page has no <title> tag defined.",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.PAGE_CONTENT,
                impact="The title tag is one of the most important on-page SEO elements. Without it, search engines can't properly understand or display your page in results.",
                fix_steps=[
                    "Add a <title> tag inside the <head> section",
                    "Write a unique, descriptive title (30-60 characters)",
                    "Include your primary keyword naturally",
                    "Make it compelling to encourage clicks",
                    "Example: <title>Your Primary Keyword - Brand Name</title>"
                ],
                expected_outcome="Your page will have a proper title displayed in search results, improving CTR and rankings.",
                validation_steps=[
                    "View page source and verify <title> tag exists in <head>",
                    "Use Google Search Console URL Inspection",
                    "Test how it appears in search results preview tools"
                ],
                difficulty="easy",
                priority_score=95
            ))
            return

        title_text = title_tag.get_text(strip=True)
        title_length = len(title_text)

        self.result.data['title'] = {
            'exists': True,
            'content': title_text,
            'length': title_length
        }

        if not title_text:
            self.result.add_issue(SEOIssue(
                title="Empty Title Tag",
                description="The title tag exists but contains no text.",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.PAGE_CONTENT,
                impact="An empty title provides no information to search engines or users.",
                fix_steps=[
                    "Add descriptive text to your title tag",
                    "Include primary keyword and brand name",
                    "Keep it between 30-60 characters"
                ],
                expected_outcome="Search engines and users will understand what your page is about.",
                validation_steps=[
                    "View page source to verify title has content"
                ],
                difficulty="easy",
                priority_score=95
            ))
        elif title_length < self.TITLE_MIN_LENGTH:
            self.result.add_issue(SEOIssue(
                title="Title Tag Too Short",
                description=f"Your title is only {title_length} characters. Recommended: {self.TITLE_MIN_LENGTH}-{self.TITLE_MAX_LENGTH} characters.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PAGE_CONTENT,
                impact="Short titles miss opportunities to include keywords and may appear incomplete in search results.",
                fix_steps=[
                    "Expand your title to include more descriptive keywords",
                    "Add your brand name if not present",
                    "Include secondary keywords or modifiers",
                    f"Aim for {self.TITLE_MIN_LENGTH}-{self.TITLE_MAX_LENGTH} characters"
                ],
                expected_outcome="Better keyword targeting and more informative search snippets.",
                validation_steps=[
                    f"Verify title length is at least {self.TITLE_MIN_LENGTH} characters"
                ],
                current_value=f"{title_length} characters: '{title_text}'",
                recommended_value=f"{self.TITLE_MIN_LENGTH}-{self.TITLE_MAX_LENGTH} characters",
                difficulty="easy",
                priority_score=60
            ))
        elif title_length > self.TITLE_MAX_LENGTH:
            self.result.add_issue(SEOIssue(
                title="Title Tag Too Long",
                description=f"Your title is {title_length} characters and will be truncated in search results. Maximum recommended: {self.TITLE_MAX_LENGTH} characters.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PAGE_CONTENT,
                impact="Google typically truncates titles longer than 60 characters, potentially cutting off important information.",
                fix_steps=[
                    "Shorten your title to under 60 characters",
                    "Front-load important keywords",
                    "Remove unnecessary words or redundancy",
                    "Consider using | or - to separate sections"
                ],
                expected_outcome="Your full title will be visible in search results without truncation.",
                validation_steps=[
                    "Use a SERP preview tool to verify title display",
                    f"Confirm title is under {self.TITLE_MAX_LENGTH} characters"
                ],
                current_value=f"{title_length} characters: '{truncate_text(title_text, 70)}'",
                recommended_value=f"Under {self.TITLE_MAX_LENGTH} characters",
                difficulty="easy",
                priority_score=55
            ))

    def _check_meta_description(self) -> None:
        """Check meta description for SEO best practices."""
        meta_desc = self.soup.find('meta', attrs={'name': re.compile(r'^description$', re.I)})

        if not meta_desc:
            self.result.data['meta_description'] = {'exists': False}
            self.result.add_issue(SEOIssue(
                title="Missing Meta Description",
                description="This page has no meta description defined.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PAGE_CONTENT,
                impact="Without a meta description, Google will auto-generate one from page content, which may not be optimal for click-through rates.",
                fix_steps=[
                    "Add a meta description tag to your <head> section",
                    "Write a compelling summary (70-160 characters)",
                    "Include your primary keyword naturally",
                    "Add a call-to-action to encourage clicks",
                    "Example: <meta name='description' content='Your compelling description here.'>"
                ],
                expected_outcome="A well-crafted meta description can improve CTR from search results.",
                validation_steps=[
                    "View page source and verify meta description exists",
                    "Preview how it appears in SERP using preview tools"
                ],
                difficulty="easy",
                priority_score=70
            ))
            return

        description_text = meta_desc.get('content', '')
        desc_length = len(description_text)

        self.result.data['meta_description'] = {
            'exists': True,
            'content': description_text,
            'length': desc_length
        }

        if not description_text:
            self.result.add_issue(SEOIssue(
                title="Empty Meta Description",
                description="The meta description tag exists but has no content.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PAGE_CONTENT,
                impact="An empty meta description is equivalent to having none - Google will auto-generate it.",
                fix_steps=[
                    "Add compelling content to your meta description",
                    "Include keywords and a clear call-to-action",
                    "Keep it between 70-160 characters"
                ],
                expected_outcome="Control over how your page appears in search results.",
                validation_steps=[
                    "Verify meta description content attribute has text"
                ],
                difficulty="easy",
                priority_score=70
            ))
        elif desc_length < self.DESCRIPTION_MIN_LENGTH:
            self.result.add_issue(SEOIssue(
                title="Meta Description Too Short",
                description=f"Your meta description is only {desc_length} characters. Recommended: {self.DESCRIPTION_MIN_LENGTH}-{self.DESCRIPTION_MAX_LENGTH} characters.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PAGE_CONTENT,
                impact="Short descriptions may not fully utilize available space in search results.",
                fix_steps=[
                    "Expand your description with more detail",
                    "Add benefits, features, or a call-to-action",
                    f"Aim for {self.DESCRIPTION_MIN_LENGTH}-{self.DESCRIPTION_MAX_LENGTH} characters"
                ],
                expected_outcome="More informative search snippets that better represent your content.",
                validation_steps=[
                    f"Verify description is at least {self.DESCRIPTION_MIN_LENGTH} characters"
                ],
                current_value=f"{desc_length} characters",
                recommended_value=f"{self.DESCRIPTION_MIN_LENGTH}-{self.DESCRIPTION_MAX_LENGTH} characters",
                difficulty="easy",
                priority_score=35
            ))
        elif desc_length > self.DESCRIPTION_MAX_LENGTH:
            self.result.add_issue(SEOIssue(
                title="Meta Description Too Long",
                description=f"Your meta description is {desc_length} characters and may be truncated. Maximum recommended: {self.DESCRIPTION_MAX_LENGTH} characters.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PAGE_CONTENT,
                impact="Descriptions over 160 characters are typically truncated, cutting off your message.",
                fix_steps=[
                    "Shorten your description to under 160 characters",
                    "Front-load the most important information",
                    "Ensure key message isn't truncated"
                ],
                expected_outcome="Your full description visible in search results.",
                validation_steps=[
                    "Use SERP preview tool to verify display",
                    f"Confirm description is under {self.DESCRIPTION_MAX_LENGTH} characters"
                ],
                current_value=f"{desc_length} characters",
                recommended_value=f"Under {self.DESCRIPTION_MAX_LENGTH} characters",
                difficulty="easy",
                priority_score=30
            ))

    def _check_heading_hierarchy(self) -> None:
        """Check heading structure for SEO and accessibility."""
        headings = {f'h{i}': self.soup.find_all(f'h{i}') for i in range(1, 7)}
        heading_counts = {tag: len(elements) for tag, elements in headings.items()}

        self.result.data['headings'] = {
            'counts': heading_counts,
            'h1_content': [h.get_text(strip=True) for h in headings['h1'][:5]]
        }

        # Check H1
        h1_count = heading_counts['h1']
        if h1_count == 0:
            self.result.add_issue(SEOIssue(
                title="Missing H1 Heading",
                description="This page has no H1 heading tag.",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.PAGE_CONTENT,
                impact="The H1 is crucial for SEO - it tells search engines what your page is about and is a significant ranking factor.",
                fix_steps=[
                    "Add exactly one H1 tag to your page",
                    "Place it near the top of your main content",
                    "Include your primary keyword naturally",
                    "Make it descriptive and unique for this page",
                    "Example: <h1>Your Primary Keyword and Topic</h1>"
                ],
                expected_outcome="Clear topical signal to search engines, potentially improving rankings for target keywords.",
                validation_steps=[
                    "View page source and search for <h1> tag",
                    "Verify only one H1 exists on the page",
                    "Confirm it contains relevant keywords"
                ],
                difficulty="easy",
                priority_score=85
            ))
        elif h1_count > 1:
            h1_texts = [h.get_text(strip=True) for h in headings['h1']]
            self.result.add_issue(SEOIssue(
                title="Multiple H1 Headings",
                description=f"This page has {h1_count} H1 headings instead of one.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PAGE_CONTENT,
                impact="Multiple H1s can dilute your page's topical focus and confuse search engines about your main topic.",
                fix_steps=[
                    "Choose the most important H1 that represents your page topic",
                    "Change other H1 tags to H2 or appropriate heading levels",
                    "Ensure heading hierarchy is logical (H1 > H2 > H3, etc.)"
                ],
                expected_outcome="Clear content hierarchy with one strong topical signal from your H1.",
                validation_steps=[
                    "Search page source for <h1> - should find only one",
                    "Use browser dev tools to inspect heading structure"
                ],
                current_value=f"{h1_count} H1 tags: {h1_texts[:3]}",
                recommended_value="Exactly 1 H1 tag",
                affected_elements=h1_texts[:5],
                difficulty="easy",
                priority_score=65
            ))
        else:
            # Check if H1 is empty
            h1_text = headings['h1'][0].get_text(strip=True)
            if not h1_text:
                self.result.add_issue(SEOIssue(
                    title="Empty H1 Heading",
                    description="The H1 tag exists but contains no text.",
                    severity=IssueSeverity.CRITICAL,
                    category=IssueCategory.PAGE_CONTENT,
                    impact="An empty H1 provides no value to search engines or users.",
                    fix_steps=[
                        "Add descriptive, keyword-rich text to your H1",
                        "Make sure it clearly describes the page content"
                    ],
                    expected_outcome="Clear topical signal from your H1 heading.",
                    validation_steps=[
                        "Verify H1 tag contains visible text"
                    ],
                    difficulty="easy",
                    priority_score=85
                ))

        # Check heading hierarchy
        self._check_heading_sequence(heading_counts)

    def _check_heading_sequence(self, heading_counts: Dict[str, int]) -> None:
        """Check for proper heading sequence (no skipped levels)."""
        levels = [heading_counts[f'h{i}'] > 0 for i in range(1, 7)]

        # Find gaps in heading sequence
        skipped_levels = []
        highest_used = 0
        for i, has_heading in enumerate(levels):
            if has_heading:
                highest_used = i + 1
                # Check if any lower level was skipped
                for j in range(highest_used - 1):
                    if not levels[j] and j + 1 not in skipped_levels:
                        skipped_levels.append(j + 1)

        if skipped_levels and heading_counts['h1'] > 0:
            self.result.add_issue(SEOIssue(
                title="Skipped Heading Levels",
                description=f"Your heading structure skips levels: H{skipped_levels}. This breaks the logical hierarchy.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PAGE_CONTENT,
                impact="Skipped heading levels can confuse screen readers and may indicate poor content structure.",
                fix_steps=[
                    "Review your heading structure",
                    "Ensure headings follow a logical order: H1 → H2 → H3",
                    "Don't skip from H1 to H3 without H2",
                    "Consider the semantic meaning of your content sections"
                ],
                expected_outcome="Proper document outline that aids accessibility and SEO.",
                validation_steps=[
                    "Use browser extensions to visualize heading structure",
                    "Run accessibility checker to verify heading order"
                ],
                current_value=f"Skipped: H{skipped_levels}",
                recommended_value="Sequential heading levels",
                difficulty="medium",
                priority_score=25
            ))

    def _check_image_optimization(self) -> None:
        """Check image optimization (alt tags, etc.)."""
        images = self.soup.find_all('img')
        total_images = len(images)

        images_without_alt = []
        images_with_empty_alt = []
        images_without_dimensions = []

        for img in images:
            src = img.get('src', img.get('data-src', ''))[:100]
            alt = img.get('alt')

            if alt is None:
                images_without_alt.append(src)
            elif alt.strip() == '':
                images_with_empty_alt.append(src)

            if not img.get('width') or not img.get('height'):
                images_without_dimensions.append(src)

        self.result.data['images'] = {
            'total': total_images,
            'without_alt': len(images_without_alt),
            'with_empty_alt': len(images_with_empty_alt),
            'without_dimensions': len(images_without_dimensions)
        }

        if images_without_alt:
            self.result.add_issue(SEOIssue(
                title="Images Missing Alt Attributes",
                description=f"{len(images_without_alt)} of {total_images} images have no alt attribute.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PAGE_CONTENT,
                impact="Missing alt text hurts accessibility and SEO. Search engines can't understand image content without it.",
                fix_steps=[
                    "Add alt attributes to all content images",
                    "Write descriptive alt text that explains the image",
                    "Include relevant keywords naturally",
                    "For decorative images, use empty alt='' (not missing entirely)",
                    "Example: <img src='image.jpg' alt='Description of image'>"
                ],
                expected_outcome="Improved image SEO, accessibility, and potential traffic from image search.",
                validation_steps=[
                    "Run accessibility checker to find images without alt",
                    "View page source and verify all img tags have alt",
                    "Use browser dev tools to inspect images"
                ],
                current_value=f"{len(images_without_alt)} images without alt",
                recommended_value="All images should have alt attributes",
                affected_elements=images_without_alt[:10],
                difficulty="medium",
                priority_score=65
            ))

        if images_without_dimensions:
            self.result.add_issue(SEOIssue(
                title="Images Missing Width/Height Attributes",
                description=f"{len(images_without_dimensions)} images lack explicit width and height attributes.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PAGE_CONTENT,
                impact="Without dimensions, browsers can't reserve space for images, causing layout shifts (poor CLS).",
                fix_steps=[
                    "Add width and height attributes to all img tags",
                    "Use the image's intrinsic dimensions",
                    "Example: <img src='image.jpg' width='800' height='600' alt='...'>",
                    "CSS can still control displayed size"
                ],
                expected_outcome="Reduced Cumulative Layout Shift (CLS) and better Core Web Vitals.",
                validation_steps=[
                    "Check img tags for width and height attributes",
                    "Run Lighthouse to measure CLS improvements"
                ],
                current_value=f"{len(images_without_dimensions)} images without dimensions",
                affected_elements=images_without_dimensions[:10],
                difficulty="medium",
                priority_score=45
            ))

    def _check_content_quality(self) -> None:
        """Check basic content quality metrics."""
        text_content = extract_text_content(self.html_content)
        word_count = len(text_content.split())
        text_ratio = calculate_text_ratio(self.html_content)

        self.result.data['content'] = {
            'word_count': word_count,
            'text_html_ratio': round(text_ratio * 100, 2)
        }

        if word_count < self.MIN_CONTENT_LENGTH:
            self.result.add_issue(SEOIssue(
                title="Thin Content",
                description=f"This page has only {word_count} words, which may be considered thin content.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PAGE_CONTENT,
                impact="Pages with little content often struggle to rank. Google favors comprehensive, valuable content.",
                fix_steps=[
                    "Expand your content to thoroughly cover the topic",
                    "Add relevant sections, FAQs, or supporting information",
                    "Aim for at least 300-500 words for basic pages",
                    "Focus on value, not just word count",
                    "Consider what questions users might have"
                ],
                expected_outcome="More comprehensive content that better satisfies user intent and ranks higher.",
                validation_steps=[
                    "Check word count using online tools",
                    "Compare content depth to top-ranking competitors"
                ],
                current_value=f"{word_count} words",
                recommended_value=f"At least {self.MIN_CONTENT_LENGTH} words",
                difficulty="medium",
                priority_score=60
            ))

        if text_ratio < 0.10:
            self.result.add_issue(SEOIssue(
                title="Low Text-to-HTML Ratio",
                description=f"Your text-to-HTML ratio is {round(text_ratio * 100, 1)}%, which is quite low.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PAGE_CONTENT,
                impact="A very low text-to-HTML ratio might indicate code bloat or insufficient content.",
                fix_steps=[
                    "Add more textual content to the page",
                    "Minify HTML, CSS, and JavaScript",
                    "Remove unnecessary code, comments, and whitespace",
                    "Consider if inline styles could be external CSS"
                ],
                expected_outcome="Better balance of content to code, potentially improving page load and SEO.",
                validation_steps=[
                    "Check text-to-HTML ratio using online tools",
                    "Review page source for unnecessary code"
                ],
                current_value=f"{round(text_ratio * 100, 1)}%",
                recommended_value="Above 10%",
                difficulty="medium",
                priority_score=30
            ))

    def _check_language_declaration(self) -> None:
        """Check for proper language declaration."""
        html_tag = self.soup.find('html')
        lang = html_tag.get('lang') if html_tag else None

        self.result.data['language'] = {
            'declared': lang is not None,
            'value': lang
        }

        if not lang:
            self.result.add_issue(SEOIssue(
                title="Missing Language Declaration",
                description="The HTML tag lacks a lang attribute specifying the page language.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PAGE_CONTENT,
                impact="Language declaration helps search engines serve your content to the right audience and aids accessibility.",
                fix_steps=[
                    "Add a lang attribute to your <html> tag",
                    "Use proper ISO language codes",
                    "Example: <html lang='en'> for English",
                    "For regional variants: <html lang='en-US'>"
                ],
                expected_outcome="Better language targeting and improved accessibility.",
                validation_steps=[
                    "Check opening <html> tag for lang attribute",
                    "Verify correct language code is used"
                ],
                recommended_value="<html lang='en'>",
                difficulty="easy",
                priority_score=25
            ))

    def _check_viewport_meta(self) -> None:
        """Check for viewport meta tag (mobile optimization)."""
        viewport = self.soup.find('meta', attrs={'name': 'viewport'})

        self.result.data['viewport'] = {
            'exists': viewport is not None,
            'content': viewport.get('content') if viewport else None
        }

        if not viewport:
            self.result.add_issue(SEOIssue(
                title="Missing Viewport Meta Tag",
                description="No viewport meta tag found. This is essential for mobile responsiveness.",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.MOBILE,
                impact="Without a viewport tag, mobile devices won't display your page properly, hurting mobile usability and rankings.",
                fix_steps=[
                    "Add a viewport meta tag to your <head> section",
                    "Standard viewport: <meta name='viewport' content='width=device-width, initial-scale=1'>",
                    "This ensures proper scaling on mobile devices"
                ],
                expected_outcome="Proper mobile rendering and improved mobile search rankings.",
                validation_steps=[
                    "View page source and verify viewport tag exists",
                    "Test page on mobile devices or Chrome DevTools mobile view",
                    "Run Google's Mobile-Friendly Test"
                ],
                recommended_value="<meta name='viewport' content='width=device-width, initial-scale=1'>",
                difficulty="easy",
                priority_score=90
            ))

    def _check_open_graph(self) -> None:
        """Check Open Graph meta tags for social sharing."""
        og_tags = {
            'og:title': self.soup.find('meta', attrs={'property': 'og:title'}),
            'og:description': self.soup.find('meta', attrs={'property': 'og:description'}),
            'og:image': self.soup.find('meta', attrs={'property': 'og:image'}),
            'og:url': self.soup.find('meta', attrs={'property': 'og:url'}),
            'og:type': self.soup.find('meta', attrs={'property': 'og:type'})
        }

        missing_tags = [tag for tag, element in og_tags.items() if not element]

        self.result.data['open_graph'] = {
            'tags_present': [tag for tag, el in og_tags.items() if el],
            'tags_missing': missing_tags
        }

        essential_og_tags = ['og:title', 'og:description', 'og:image']
        missing_essential = [tag for tag in essential_og_tags if tag in missing_tags]

        if missing_essential:
            self.result.add_issue(SEOIssue(
                title="Missing Essential Open Graph Tags",
                description=f"Missing Open Graph tags: {', '.join(missing_essential)}",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PAGE_CONTENT,
                impact="Without Open Graph tags, social media platforms can't properly display your content when shared.",
                fix_steps=[
                    "Add missing Open Graph tags to your <head>",
                    "<meta property='og:title' content='Your Page Title'>",
                    "<meta property='og:description' content='Your description'>",
                    "<meta property='og:image' content='https://example.com/image.jpg'>",
                    "Ensure og:image is at least 1200x630 pixels for best display"
                ],
                expected_outcome="Better social media presence with rich previews when your content is shared.",
                validation_steps=[
                    "Use Facebook's Sharing Debugger to test",
                    "Use Twitter Card Validator for Twitter display",
                    "View page source and verify OG tags exist"
                ],
                current_value=f"Missing: {', '.join(missing_essential)}",
                recommended_value="og:title, og:description, og:image",
                difficulty="easy",
                priority_score=35
            ))
