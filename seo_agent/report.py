"""
SEO Audit Report Generator - Creates formatted, prioritized reports.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .analyzers.base import SEOIssue, IssueSeverity, AnalysisResult


@dataclass
class AuditReport:
    """Complete SEO audit report."""
    url: str
    audit_date: str
    analysis_results: Dict[str, AnalysisResult] = field(default_factory=dict)
    critical_issues: List[SEOIssue] = field(default_factory=list)
    important_issues: List[SEOIssue] = field(default_factory=list)
    recommended_issues: List[SEOIssue] = field(default_factory=list)
    summary_data: Dict[str, Any] = field(default_factory=dict)

    def add_result(self, result: AnalysisResult) -> None:
        """Add an analysis result to the report."""
        self.analysis_results[result.analyzer_name] = result
        for issue in result.issues:
            if issue.severity == IssueSeverity.CRITICAL:
                self.critical_issues.append(issue)
            elif issue.severity == IssueSeverity.IMPORTANT:
                self.important_issues.append(issue)
            else:
                self.recommended_issues.append(issue)

    def sort_issues_by_priority(self) -> None:
        """Sort all issues by priority score."""
        self.critical_issues.sort(key=lambda x: x.priority_score, reverse=True)
        self.important_issues.sort(key=lambda x: x.priority_score, reverse=True)
        self.recommended_issues.sort(key=lambda x: x.priority_score, reverse=True)

    def get_total_issues(self) -> int:
        """Get total number of issues found."""
        return len(self.critical_issues) + len(self.important_issues) + len(self.recommended_issues)

    def calculate_score(self) -> int:
        """Calculate an overall SEO score (0-100)."""
        if self.get_total_issues() == 0:
            return 100

        # Weighted penalty system
        penalty = 0
        penalty += len(self.critical_issues) * 15
        penalty += len(self.important_issues) * 8
        penalty += len(self.recommended_issues) * 3

        score = max(0, 100 - penalty)
        return score


class ReportGenerator:
    """Generates formatted SEO audit reports."""

    # ANSI color codes
    COLORS = {
        'red': '\033[91m',
        'yellow': '\033[93m',
        'green': '\033[92m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'bold': '\033[1m',
        'reset': '\033[0m'
    }

    def __init__(self, use_colors: bool = True):
        """Initialize the report generator."""
        self.use_colors = use_colors

    def _color(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.use_colors:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def _bold(self, text: str) -> str:
        """Make text bold if colors are enabled."""
        if not self.use_colors:
            return text
        return f"{self.COLORS['bold']}{text}{self.COLORS['reset']}"

    def _severity_color(self, severity: IssueSeverity) -> str:
        """Get color for severity level."""
        if severity == IssueSeverity.CRITICAL:
            return 'red'
        elif severity == IssueSeverity.IMPORTANT:
            return 'yellow'
        return 'cyan'

    def _format_issue(self, issue: SEOIssue, index: int) -> str:
        """Format a single issue for display."""
        lines = []
        color = self._severity_color(issue.severity)

        # Issue header
        lines.append(f"\n{self._color(f'{index}. {issue.title}', color)}")
        lines.append(f"   {self._bold('Category:')} {issue.category.value.replace('_', ' ').title()}")
        lines.append(f"   {self._bold('Difficulty:')} {issue.difficulty.title()}")

        # Description
        whats_wrong = "What's wrong:"
        lines.append(f"\n   {self._bold(whats_wrong)}")
        lines.append(f"   {issue.description}")

        # Impact
        lines.append(f"\n   {self._bold('Why it matters:')}")
        lines.append(f"   {issue.impact}")

        # Current vs Recommended values
        if issue.current_value:
            lines.append(f"\n   {self._bold('Current:')} {issue.current_value}")
        if issue.recommended_value:
            lines.append(f"   {self._bold('Recommended:')} {issue.recommended_value}")

        # Affected elements
        if issue.affected_elements:
            lines.append(f"\n   {self._bold('Affected elements:')}")
            for elem in issue.affected_elements[:5]:
                lines.append(f"   - {elem}")
            if len(issue.affected_elements) > 5:
                lines.append(f"   ... and {len(issue.affected_elements) - 5} more")

        # Fix steps
        lines.append(f"\n   {self._bold('How to fix:')}")
        for i, step in enumerate(issue.fix_steps, 1):
            if step.startswith('  '):  # Sub-step or example
                lines.append(f"      {step}")
            else:
                lines.append(f"   {i}. {step}")

        # Expected outcome
        lines.append(f"\n   {self._bold('Expected outcome:')}")
        lines.append(f"   {issue.expected_outcome}")

        # Validation
        lines.append(f"\n   {self._bold('How to validate:')}")
        for step in issue.validation_steps:
            lines.append(f"   - {step}")

        return '\n'.join(lines)

    def generate_console_report(self, report: AuditReport) -> str:
        """Generate a formatted console report."""
        lines = []

        # Header
        lines.append("\n" + "=" * 70)
        lines.append(self._bold(self._color("SEO AUDIT REPORT", 'white')))
        lines.append("=" * 70)
        lines.append(f"URL: {report.url}")
        lines.append(f"Date: {report.audit_date}")

        # Score
        score = report.calculate_score()
        score_color = 'green' if score >= 80 else 'yellow' if score >= 50 else 'red'
        lines.append(f"\n{self._bold('Overall SEO Score:')} {self._color(f'{score}/100', score_color)}")

        # Summary
        lines.append(f"\n{self._bold('Issues Found:')}")
        lines.append(f"  {self._color(f'Critical: {len(report.critical_issues)}', 'red')}")
        lines.append(f"  {self._color(f'Important: {len(report.important_issues)}', 'yellow')}")
        lines.append(f"  {self._color(f'Recommended: {len(report.recommended_issues)}', 'cyan')}")

        # Quick data summary
        if report.analysis_results:
            lines.append(f"\n{self._bold('Quick Stats:')}")

            # Page data
            for name, result in report.analysis_results.items():
                if 'title' in result.data:
                    title_len = result.data['title'].get('length', 0)
                    lines.append(f"  Title length: {title_len} characters")
                if 'meta_description' in result.data:
                    desc_len = result.data['meta_description'].get('length', 0)
                    lines.append(f"  Meta description: {desc_len} characters")
                if 'headings' in result.data:
                    h1_count = result.data['headings'].get('counts', {}).get('h1', 0)
                    lines.append(f"  H1 tags: {h1_count}")
                if 'images' in result.data:
                    img_data = result.data['images']
                    lines.append(f"  Images: {img_data.get('total', 0)} total, {img_data.get('without_alt', 0)} missing alt")
                if 'links' in result.data:
                    link_data = result.data['links']
                    lines.append(f"  Links: {link_data.get('internal_count', 0)} internal, {link_data.get('external_count', 0)} external")
                if 'https' in result.data:
                    https = result.data['https'].get('enabled', False)
                    lines.append(f"  HTTPS: {'Yes' if https else 'No'}")
                if 'schema_types' in result.data:
                    schemas = result.data['schema_types']
                    if schemas:
                        lines.append(f"  Schema types: {', '.join(schemas[:5])}")

        # Critical Issues
        if report.critical_issues:
            lines.append("\n" + "=" * 70)
            lines.append(self._bold(self._color("1. CRITICAL ISSUES - Fix Immediately", 'red')))
            lines.append("=" * 70)
            lines.append(self._color("These issues have the highest impact on your SEO and should be addressed first.", 'red'))

            for i, issue in enumerate(report.critical_issues, 1):
                lines.append(self._format_issue(issue, i))

        # Important Issues
        if report.important_issues:
            lines.append("\n" + "=" * 70)
            lines.append(self._bold(self._color("2. IMPORTANT OPTIMIZATIONS - Fix Soon", 'yellow')))
            lines.append("=" * 70)
            lines.append(self._color("These issues have medium impact and should be fixed in the near term.", 'yellow'))

            for i, issue in enumerate(report.important_issues, 1):
                lines.append(self._format_issue(issue, i))

        # Recommended Issues
        if report.recommended_issues:
            lines.append("\n" + "=" * 70)
            lines.append(self._bold(self._color("3. RECOMMENDED ENHANCEMENTS - Nice to Have", 'cyan')))
            lines.append("=" * 70)
            lines.append(self._color("These improvements can further enhance your SEO but are lower priority.", 'cyan'))

            for i, issue in enumerate(report.recommended_issues, 1):
                lines.append(self._format_issue(issue, i))

        # No issues case
        if report.get_total_issues() == 0:
            lines.append("\n" + "=" * 70)
            lines.append(self._bold(self._color("No SEO issues found!", 'green')))
            lines.append("=" * 70)
            lines.append("Your page appears to follow SEO best practices. Great job!")

        # Footer
        lines.append("\n" + "=" * 70)
        lines.append(self._bold("NEXT STEPS"))
        lines.append("=" * 70)

        if report.critical_issues:
            lines.append(f"1. Address the {len(report.critical_issues)} critical issue(s) first")
            lines.append("2. Test changes with Google's tools:")
            lines.append("   - Rich Results Test: https://search.google.com/test/rich-results")
            lines.append("   - PageSpeed Insights: https://pagespeed.web.dev/")
            lines.append("   - Mobile-Friendly Test: https://search.google.com/test/mobile-friendly")
            lines.append("3. Monitor progress in Google Search Console")
        elif report.important_issues:
            lines.append(f"1. Work through the {len(report.important_issues)} important optimization(s)")
            lines.append("2. Validate fixes with testing tools")
            lines.append("3. Re-run this audit after making changes")
        else:
            lines.append("1. Consider implementing the recommended enhancements")
            lines.append("2. Continue monitoring Core Web Vitals")
            lines.append("3. Keep content fresh and up-to-date")

        lines.append("\n" + "=" * 70)

        return '\n'.join(lines)

    def generate_json_report(self, report: AuditReport) -> str:
        """Generate a JSON report."""
        data = {
            'url': report.url,
            'audit_date': report.audit_date,
            'score': report.calculate_score(),
            'summary': {
                'critical_count': len(report.critical_issues),
                'important_count': len(report.important_issues),
                'recommended_count': len(report.recommended_issues),
                'total_issues': report.get_total_issues()
            },
            'analysis_data': {},
            'issues': {
                'critical': [issue.to_dict() for issue in report.critical_issues],
                'important': [issue.to_dict() for issue in report.important_issues],
                'recommended': [issue.to_dict() for issue in report.recommended_issues]
            }
        }

        # Add analysis data
        for name, result in report.analysis_results.items():
            data['analysis_data'][name] = result.data

        return json.dumps(data, indent=2)

    def generate_markdown_report(self, report: AuditReport) -> str:
        """Generate a Markdown report."""
        lines = []

        # Header
        lines.append(f"# SEO Audit Report")
        lines.append(f"\n**URL:** {report.url}")
        lines.append(f"**Date:** {report.audit_date}")
        lines.append(f"**Score:** {report.calculate_score()}/100")

        # Summary
        lines.append(f"\n## Summary")
        lines.append(f"\n| Severity | Count |")
        lines.append(f"|----------|-------|")
        lines.append(f"| Critical | {len(report.critical_issues)} |")
        lines.append(f"| Important | {len(report.important_issues)} |")
        lines.append(f"| Recommended | {len(report.recommended_issues)} |")

        # Issues
        def format_md_issue(issue: SEOIssue, index: int) -> List[str]:
            md = []
            md.append(f"\n### {index}. {issue.title}")
            md.append(f"\n**Category:** {issue.category.value}")
            md.append(f"**Difficulty:** {issue.difficulty}")
            md.append(f"\n**Description:** {issue.description}")
            md.append(f"\n**Impact:** {issue.impact}")

            if issue.current_value:
                md.append(f"\n**Current:** {issue.current_value}")
            if issue.recommended_value:
                md.append(f"**Recommended:** {issue.recommended_value}")

            md.append(f"\n**How to fix:**")
            for i, step in enumerate(issue.fix_steps, 1):
                md.append(f"{i}. {step}")

            md.append(f"\n**Expected outcome:** {issue.expected_outcome}")

            md.append(f"\n**Validation:**")
            for step in issue.validation_steps:
                md.append(f"- {step}")

            return md

        if report.critical_issues:
            lines.append(f"\n## Critical Issues")
            for i, issue in enumerate(report.critical_issues, 1):
                lines.extend(format_md_issue(issue, i))

        if report.important_issues:
            lines.append(f"\n## Important Optimizations")
            for i, issue in enumerate(report.important_issues, 1):
                lines.extend(format_md_issue(issue, i))

        if report.recommended_issues:
            lines.append(f"\n## Recommended Enhancements")
            for i, issue in enumerate(report.recommended_issues, 1):
                lines.extend(format_md_issue(issue, i))

        return '\n'.join(lines)
