"""
Structured Data Analyzer - Checks Schema.org markup and rich snippets.
"""

import json
import re
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

from .base import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity, IssueCategory


class StructuredDataAnalyzer(BaseAnalyzer):
    """Analyzer for structured data and schema markup."""

    name = "structured_data"

    # Common schema types for different page types
    RECOMMENDED_SCHEMAS = {
        'homepage': ['Organization', 'WebSite', 'LocalBusiness'],
        'article': ['Article', 'NewsArticle', 'BlogPosting'],
        'product': ['Product', 'Offer'],
        'local_business': ['LocalBusiness', 'Organization'],
        'person': ['Person'],
        'event': ['Event'],
        'recipe': ['Recipe'],
        'faq': ['FAQPage', 'Question'],
        'howto': ['HowTo'],
        'review': ['Review', 'AggregateRating']
    }

    def __init__(self, url: str, html_content: str, response_headers: Dict[str, str]):
        super().__init__(url, html_content, response_headers)
        self.soup = BeautifulSoup(html_content, 'lxml')

    def analyze(self) -> AnalysisResult:
        """Perform structured data analysis."""
        try:
            self._extract_structured_data()
            self._check_schema_presence()
            self._validate_structured_data()
            self._check_breadcrumbs()
            self.result.success = True
        except Exception as e:
            self.result.success = False
            self.result.error = str(e)

        return self.result

    def _extract_structured_data(self) -> None:
        """Extract all structured data from the page."""
        structured_data = {
            'json_ld': [],
            'microdata': [],
            'rdfa': []
        }

        # Extract JSON-LD
        json_ld_scripts = self.soup.find_all('script', attrs={'type': 'application/ld+json'})
        for script in json_ld_scripts:
            try:
                content = script.string
                if content:
                    data = json.loads(content)
                    structured_data['json_ld'].append(data)
            except json.JSONDecodeError:
                pass  # Will be caught in validation

        # Extract Microdata
        microdata_items = self.soup.find_all(attrs={'itemscope': True})
        for item in microdata_items:
            item_type = item.get('itemtype', '')
            structured_data['microdata'].append({
                'type': item_type,
                'element': item.name
            })

        # Extract RDFa
        rdfa_items = self.soup.find_all(attrs={'typeof': True})
        for item in rdfa_items:
            item_type = item.get('typeof', '')
            structured_data['rdfa'].append({
                'type': item_type,
                'element': item.name
            })

        self.result.data['structured_data'] = structured_data

        # Extract schema types found
        schema_types = set()
        for item in structured_data['json_ld']:
            if isinstance(item, dict):
                schema_type = item.get('@type')
                if schema_type:
                    if isinstance(schema_type, list):
                        schema_types.update(schema_type)
                    else:
                        schema_types.add(schema_type)
                # Check @graph
                if '@graph' in item:
                    for graph_item in item['@graph']:
                        if isinstance(graph_item, dict):
                            graph_type = graph_item.get('@type')
                            if graph_type:
                                if isinstance(graph_type, list):
                                    schema_types.update(graph_type)
                                else:
                                    schema_types.add(graph_type)

        for item in structured_data['microdata']:
            if item.get('type'):
                # Extract type name from URL
                type_name = item['type'].split('/')[-1]
                schema_types.add(type_name)

        self.result.data['schema_types'] = list(schema_types)

    def _check_schema_presence(self) -> None:
        """Check if structured data is present."""
        sd = self.result.data.get('structured_data', {})
        has_structured_data = (
            sd.get('json_ld') or
            sd.get('microdata') or
            sd.get('rdfa')
        )

        if not has_structured_data:
            self.result.add_issue(SEOIssue(
                title="No Structured Data Found",
                description="This page has no Schema.org structured data markup.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.STRUCTURED_DATA,
                impact="Without structured data, your page won't be eligible for rich snippets in search results, missing out on enhanced visibility and higher CTR.",
                fix_steps=[
                    "Identify what type of content your page has",
                    "Choose appropriate schema types:",
                    "  - Organization/LocalBusiness for company pages",
                    "  - Article/BlogPosting for content pages",
                    "  - Product for e-commerce product pages",
                    "  - FAQPage for FAQ sections",
                    "Add JSON-LD structured data in a <script type='application/ld+json'> tag",
                    "Use Google's Structured Data Markup Helper to generate code",
                    "Example for Organization:",
                    '  {"@context": "https://schema.org", "@type": "Organization", "name": "Your Company", "url": "https://example.com"}'
                ],
                expected_outcome="Eligibility for rich snippets, enhanced search appearance, potentially higher CTR.",
                validation_steps=[
                    "Use Google's Rich Results Test (search.google.com/test/rich-results)",
                    "Check Schema.org validator (validator.schema.org)",
                    "Monitor Search Console for rich result reports"
                ],
                difficulty="medium",
                priority_score=65
            ))
        else:
            # Check for recommended basic schemas
            schema_types = set(self.result.data.get('schema_types', []))

            # Check for Organization/WebSite schema (good for any site)
            has_org = 'Organization' in schema_types or 'LocalBusiness' in schema_types
            has_website = 'WebSite' in schema_types

            if not has_org and not has_website:
                self.result.add_issue(SEOIssue(
                    title="Missing Basic Organization/WebSite Schema",
                    description="Page lacks Organization or WebSite schema markup.",
                    severity=IssueSeverity.RECOMMENDED,
                    category=IssueCategory.STRUCTURED_DATA,
                    impact="Organization and WebSite schemas help establish your brand in search results and enable sitelinks search box.",
                    fix_steps=[
                        "Add Organization schema with your company details:",
                        '  {"@context": "https://schema.org", "@type": "Organization",',
                        '   "name": "Company Name", "url": "https://example.com",',
                        '   "logo": "https://example.com/logo.png",',
                        '   "sameAs": ["https://twitter.com/company", "https://facebook.com/company"]}',
                        "Add WebSite schema for sitelinks search box:",
                        '  {"@context": "https://schema.org", "@type": "WebSite",',
                        '   "name": "Site Name", "url": "https://example.com",',
                        '   "potentialAction": {"@type": "SearchAction", "target": "https://example.com/search?q={search_term_string}"}}',
                    ],
                    expected_outcome="Enhanced brand presence in search, potential sitelinks search box.",
                    validation_steps=[
                        "Test with Google's Rich Results Test",
                        "Verify logo appears in Knowledge Panel"
                    ],
                    difficulty="easy",
                    priority_score=40
                ))

    def _validate_structured_data(self) -> None:
        """Validate structured data for common errors."""
        json_ld_data = self.result.data.get('structured_data', {}).get('json_ld', [])

        # Check for parsing errors
        json_ld_scripts = self.soup.find_all('script', attrs={'type': 'application/ld+json'})
        for i, script in enumerate(json_ld_scripts):
            content = script.string
            if content:
                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    self.result.add_issue(SEOIssue(
                        title="Invalid JSON-LD Syntax",
                        description=f"JSON-LD block #{i+1} contains invalid JSON: {str(e)[:100]}",
                        severity=IssueSeverity.CRITICAL,
                        category=IssueCategory.STRUCTURED_DATA,
                        impact="Invalid JSON will be completely ignored by search engines, providing no SEO benefit.",
                        fix_steps=[
                            "Find the JSON-LD script tag in your HTML",
                            "Use a JSON validator to identify syntax errors",
                            "Common issues: trailing commas, missing quotes, unescaped characters",
                            "Fix the JSON syntax errors",
                            "Re-validate with Google's Rich Results Test"
                        ],
                        expected_outcome="Valid JSON-LD that search engines can parse and use.",
                        validation_steps=[
                            "Paste JSON into jsonlint.com to validate syntax",
                            "Test with Google's Rich Results Test"
                        ],
                        difficulty="easy",
                        priority_score=85
                    ))

        # Validate structure of JSON-LD
        for data in json_ld_data:
            if isinstance(data, dict):
                self._validate_json_ld_item(data)

    def _validate_json_ld_item(self, data: Dict[str, Any]) -> None:
        """Validate a single JSON-LD item."""
        # Check for required @context
        if '@context' not in data:
            self.result.add_issue(SEOIssue(
                title="JSON-LD Missing @context",
                description="Structured data is missing the @context declaration.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.STRUCTURED_DATA,
                impact="Without @context, search engines may not properly interpret your structured data.",
                fix_steps=[
                    "Add @context to your JSON-LD:",
                    '  "@context": "https://schema.org"',
                    "This should be at the root level of your JSON-LD object"
                ],
                expected_outcome="Properly defined schema context for accurate parsing.",
                validation_steps=[
                    "Verify @context exists in JSON-LD",
                    "Test with structured data testing tools"
                ],
                recommended_value='"@context": "https://schema.org"',
                difficulty="easy",
                priority_score=75
            ))

        # Check for @type
        if '@type' not in data and '@graph' not in data:
            self.result.add_issue(SEOIssue(
                title="JSON-LD Missing @type",
                description="Structured data is missing the @type declaration.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.STRUCTURED_DATA,
                impact="Without @type, search engines don't know what kind of entity your data describes.",
                fix_steps=[
                    "Add @type to specify the schema type:",
                    '  "@type": "Article" (or appropriate type)',
                    "Choose from schema.org types that match your content"
                ],
                expected_outcome="Clearly defined entity type for rich result eligibility.",
                validation_steps=[
                    "Verify @type exists in JSON-LD",
                    "Confirm type matches your content"
                ],
                difficulty="easy",
                priority_score=75
            ))

        # Check for common required properties based on type
        schema_type = data.get('@type')
        if schema_type:
            self._check_required_properties(data, schema_type)

    def _check_required_properties(self, data: Dict[str, Any], schema_type: str) -> None:
        """Check required properties for common schema types."""
        required_properties = {
            'Article': ['headline', 'author', 'datePublished'],
            'NewsArticle': ['headline', 'author', 'datePublished'],
            'BlogPosting': ['headline', 'author', 'datePublished'],
            'Product': ['name', 'image'],
            'LocalBusiness': ['name', 'address'],
            'Organization': ['name'],
            'Person': ['name'],
            'Event': ['name', 'startDate', 'location'],
            'Recipe': ['name', 'image', 'recipeIngredient'],
            'FAQPage': ['mainEntity'],
            'HowTo': ['name', 'step'],
            'Review': ['itemReviewed', 'reviewRating', 'author']
        }

        if schema_type in required_properties:
            missing = [prop for prop in required_properties[schema_type] if prop not in data]
            if missing:
                self.result.add_issue(SEOIssue(
                    title=f"{schema_type} Schema Missing Required Properties",
                    description=f"Your {schema_type} schema is missing: {', '.join(missing)}",
                    severity=IssueSeverity.IMPORTANT,
                    category=IssueCategory.STRUCTURED_DATA,
                    impact=f"Missing required properties may prevent rich result eligibility for {schema_type}.",
                    fix_steps=[
                        f"Add the missing properties to your {schema_type} schema:",
                        *[f"  - Add '{prop}' with appropriate value" for prop in missing],
                        "Refer to schema.org documentation for property formats",
                        "Test with Google's Rich Results Test after changes"
                    ],
                    expected_outcome=f"Complete {schema_type} schema eligible for rich results.",
                    validation_steps=[
                        "Use Google's Rich Results Test",
                        "Check schema.org validator for completeness"
                    ],
                    current_value=f"Missing: {', '.join(missing)}",
                    recommended_value=f"Include: {', '.join(required_properties[schema_type])}",
                    difficulty="medium",
                    priority_score=60
                ))

    def _check_breadcrumbs(self) -> None:
        """Check for breadcrumb structured data and HTML."""
        schema_types = self.result.data.get('schema_types', [])
        has_breadcrumb_schema = 'BreadcrumbList' in schema_types

        # Check for breadcrumb HTML patterns
        breadcrumb_selectors = [
            self.soup.find(class_=re.compile(r'breadcrumb', re.I)),
            self.soup.find(attrs={'aria-label': re.compile(r'breadcrumb', re.I)}),
            self.soup.find('nav', class_=re.compile(r'breadcrumb', re.I)),
            self.soup.find(attrs={'itemtype': re.compile(r'BreadcrumbList', re.I)})
        ]

        has_breadcrumb_html = any(breadcrumb_selectors)

        self.result.data['breadcrumbs'] = {
            'has_schema': has_breadcrumb_schema,
            'has_html': has_breadcrumb_html
        }

        if has_breadcrumb_html and not has_breadcrumb_schema:
            self.result.add_issue(SEOIssue(
                title="Breadcrumbs Missing Schema Markup",
                description="Breadcrumb navigation found but lacks BreadcrumbList structured data.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.STRUCTURED_DATA,
                impact="Breadcrumb schema can show your site structure in search results, improving appearance and CTR.",
                fix_steps=[
                    "Add BreadcrumbList JSON-LD schema:",
                    '  {"@context": "https://schema.org", "@type": "BreadcrumbList",',
                    '   "itemListElement": [',
                    '     {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://example.com"},',
                    '     {"@type": "ListItem", "position": 2, "name": "Category", "item": "https://example.com/category"}',
                    '   ]}',
                    "Match breadcrumb items to your visible navigation"
                ],
                expected_outcome="Breadcrumb trail displayed in search results, showing page hierarchy.",
                validation_steps=[
                    "Test with Google's Rich Results Test",
                    "Verify breadcrumb display in search results"
                ],
                difficulty="easy",
                priority_score=35
            ))
