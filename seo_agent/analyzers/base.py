"""
Base analyzer class and common structures.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class IssueSeverity(Enum):
    """Severity levels for SEO issues."""
    CRITICAL = "critical"
    IMPORTANT = "important"
    RECOMMENDED = "recommended"


class IssueCategory(Enum):
    """Categories for SEO issues."""
    CRAWLABILITY = "crawlability"
    PAGE_CONTENT = "page_content"
    PERFORMANCE = "performance"
    SECURITY = "security"
    STRUCTURED_DATA = "structured_data"
    LINKS = "links"
    MOBILE = "mobile"


@dataclass
class SEOIssue:
    """Represents an SEO issue found during analysis."""
    title: str
    description: str
    severity: IssueSeverity
    category: IssueCategory
    impact: str
    fix_steps: List[str]
    expected_outcome: str
    validation_steps: List[str]
    affected_elements: List[str] = field(default_factory=list)
    current_value: Optional[str] = None
    recommended_value: Optional[str] = None
    difficulty: str = "medium"  # easy, medium, hard
    priority_score: int = 50  # 0-100, higher = more important

    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "impact": self.impact,
            "fix_steps": self.fix_steps,
            "expected_outcome": self.expected_outcome,
            "validation_steps": self.validation_steps,
            "affected_elements": self.affected_elements,
            "current_value": self.current_value,
            "recommended_value": self.recommended_value,
            "difficulty": self.difficulty,
            "priority_score": self.priority_score,
        }


@dataclass
class AnalysisResult:
    """Result from an analyzer."""
    analyzer_name: str
    issues: List[SEOIssue] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    def add_issue(self, issue: SEOIssue) -> None:
        """Add an issue to the results."""
        self.issues.append(issue)

    def get_critical_issues(self) -> List[SEOIssue]:
        """Get all critical issues."""
        return [i for i in self.issues if i.severity == IssueSeverity.CRITICAL]

    def get_important_issues(self) -> List[SEOIssue]:
        """Get all important issues."""
        return [i for i in self.issues if i.severity == IssueSeverity.IMPORTANT]

    def get_recommended_issues(self) -> List[SEOIssue]:
        """Get all recommended issues."""
        return [i for i in self.issues if i.severity == IssueSeverity.RECOMMENDED]


class BaseAnalyzer:
    """Base class for all SEO analyzers."""

    name: str = "base"

    def __init__(self, url: str, html_content: str, response_headers: Dict[str, str]):
        """Initialize the analyzer."""
        self.url = url
        self.html_content = html_content
        self.response_headers = response_headers
        self.result = AnalysisResult(analyzer_name=self.name)

    def analyze(self) -> AnalysisResult:
        """Perform the analysis. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement analyze()")

    def create_issue(
        self,
        title: str,
        description: str,
        severity: IssueSeverity,
        category: IssueCategory,
        impact: str,
        fix_steps: List[str],
        expected_outcome: str,
        validation_steps: List[str],
        **kwargs
    ) -> SEOIssue:
        """Helper method to create an issue."""
        return SEOIssue(
            title=title,
            description=description,
            severity=severity,
            category=category,
            impact=impact,
            fix_steps=fix_steps,
            expected_outcome=expected_outcome,
            validation_steps=validation_steps,
            **kwargs
        )
