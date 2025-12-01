"""
Vercel Serverless Function for SEO Audit API
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import traceback

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class handler(BaseHTTPRequestHandler):
    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_json(200, {"status": "ok"})

    def do_GET(self):
        self.send_json(200, {"name": "SEO Audit Agent API", "version": "1.0.0"})

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
            url = data.get('url', '').strip()

            if not url:
                self.send_json(400, {"error": "Missing 'url' parameter"})
                return

            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            # Import here to get better error messages
            try:
                from seo_agent import SEOAuditAgent
            except ImportError as e:
                self.send_json(500, {"error": f"Import error: {str(e)}", "trace": traceback.format_exc()})
                return

            agent = SEOAuditAgent(timeout=25)
            report = agent.audit(url)

            if 'fetch_error' in report.summary_data:
                self.send_json(400, {"error": f"Could not fetch URL: {report.summary_data['fetch_error']}"})
                return

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
                    "critical": [self.issue_to_dict(i) for i in report.critical_issues],
                    "important": [self.issue_to_dict(i) for i in report.important_issues],
                    "recommended": [self.issue_to_dict(i) for i in report.recommended_issues]
                }
            }

            self.send_json(200, result)

        except json.JSONDecodeError as e:
            self.send_json(400, {"error": f"Invalid JSON: {str(e)}"})
        except Exception as e:
            self.send_json(500, {"error": str(e), "type": type(e).__name__, "trace": traceback.format_exc()})

    def issue_to_dict(self, issue):
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
