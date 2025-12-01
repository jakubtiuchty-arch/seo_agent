"""
Vercel Serverless Function for SEO Audit API
"""

import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from seo_agent import SEOAuditAgent


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - return API info."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        response = {
            "name": "SEO Audit Agent API",
            "version": "1.0.0",
            "usage": "POST /api/audit with JSON body: {\"url\": \"https://example.com\"}"
        }
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        """Handle POST requests - run SEO audit."""
        # CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}

            url = data.get('url', '').strip()

            if not url:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Missing 'url' parameter"
                }).encode())
                return

            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            # Create agent and run audit
            agent = SEOAuditAgent(timeout=15)
            report = agent.audit(url)

            # Check for fetch errors
            if 'fetch_error' in report.summary_data:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": f"Could not fetch URL: {report.summary_data['fetch_error']}"
                }).encode())
                return

            # Generate JSON report
            result = {
                "url": report.url,
                "audit_date": report.audit_date,
                "score": report.calculate_score(),
                "summary": {
                    "critical_count": len(report.critical_issues),
                    "important_count": len(report.important_issues),
                    "recommended_count": len(report.recommended_issues),
                    "total_issues": report.get_total_issues()
                },
                "issues": {
                    "critical": [self._issue_to_dict(issue) for issue in report.critical_issues],
                    "important": [self._issue_to_dict(issue) for issue in report.important_issues],
                    "recommended": [self._issue_to_dict(issue) for issue in report.recommended_issues]
                },
                "data": {}
            }

            # Add analysis data
            for name, analysis_result in report.analysis_results.items():
                result["data"][name] = analysis_result.data

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode())

        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Invalid JSON in request body"
            }).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": str(e)
            }).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _issue_to_dict(self, issue):
        """Convert SEOIssue to dictionary."""
        return {
            "title": issue.title,
            "description": issue.description,
            "severity": issue.severity.value,
            "category": issue.category.value,
            "impact": issue.impact,
            "fix_steps": issue.fix_steps,
            "expected_outcome": issue.expected_outcome,
            "validation_steps": issue.validation_steps,
            "affected_elements": issue.affected_elements,
            "current_value": issue.current_value,
            "recommended_value": issue.recommended_value,
            "difficulty": issue.difficulty,
            "priority_score": issue.priority_score
        }
