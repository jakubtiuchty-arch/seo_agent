from flask import Flask, request, jsonify
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)


def issue_to_dict(issue):
    return {
        "title": issue.title,
        "description": issue.description,
        "severity": issue.severity.value,
        "category": issue.category.value,
        "impact": issue.impact,
        "fix_steps": issue.fix_steps,
        "expected_outcome": issue.expected_outcome,
        "validation_steps": issue.validation_steps,
        "affected_elements": issue.affected_elements[:5] if issue.affected_elements else [],
        "current_value": issue.current_value,
        "recommended_value": issue.recommended_value,
        "difficulty": issue.difficulty,
        "priority_score": issue.priority_score
    }


@app.route("/api/audit", methods=["GET"])
def get_info():
    return jsonify({
        "name": "SEO Audit Agent API",
        "version": "1.0.0",
        "usage": "POST /api/audit with JSON body: {\"url\": \"https://example.com\"}"
    })


@app.route("/api/audit", methods=["POST"])
def run_audit():
    try:
        data = request.get_json() or {}
        url = data.get("url", "").strip()

        if not url:
            return jsonify({"error": "Missing 'url' parameter"}), 400

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # Import here to catch errors
        from seo_agent import SEOAuditAgent

        agent = SEOAuditAgent(timeout=25)
        report = agent.audit(url)

        if "fetch_error" in report.summary_data:
            return jsonify({
                "error": f"Could not fetch URL: {report.summary_data['fetch_error']}"
            }), 400

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
                "critical": [issue_to_dict(i) for i in report.critical_issues],
                "important": [issue_to_dict(i) for i in report.important_issues],
                "recommended": [issue_to_dict(i) for i in report.recommended_issues]
            }
        }

        return jsonify(result)

    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


@app.route("/api/audit", methods=["OPTIONS"])
def options():
    return "", 200


# For Vercel
app = app
