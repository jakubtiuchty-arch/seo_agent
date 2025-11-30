#!/usr/bin/env python3
"""
SEO Audit Agent - Command Line Interface

A comprehensive technical SEO audit tool that analyzes websites and provides
prioritized, actionable optimization recommendations.

Usage:
    python main.py <url> [options]

Examples:
    python main.py https://example.com
    python main.py https://example.com --format json
    python main.py https://example.com --no-colors
    python main.py https://example.com --output report.md --format markdown
"""

import sys
import argparse
from typing import Optional

from seo_agent import SEOAuditAgent


def print_banner():
    """Print the SEO Agent banner."""
    banner = """
 ____  _____ ___       _             _ _ _      _                    _
/ ___|| ____/ _ \\     / \\  _   _  __| (_) |_   / \\   __ _  ___ _ __ | |_
\\___ \\|  _|| | | |   / _ \\| | | |/ _` | | __| / _ \\ / _` |/ _ \\ '_ \\| __|
 ___) | |__| |_| |  / ___ \\ |_| | (_| | | |_ / ___ \\ (_| |  __/ | | | |_
|____/|_____\\___/  /_/   \\_\\__,_|\\__,_|_|\\__/_/   \\_\\__, |\\___|_| |_|\\__|
                                                    |___/
    Technical SEO Audit Tool v1.0
    """
    print(banner)


def get_user_goal() -> str:
    """Interactively get the user's SEO goal."""
    print("""
Before we dive into the audit findings, I'd like to understand your primary goal.
What's driving your SEO audit today?

  1. Traffic Growth - Looking to increase organic search traffic
  2. Technical Fixes - Addressing known technical SEO issues
  3. Migration Prep - Preparing for a site migration or redesign
  4. Performance - Improving Core Web Vitals and page speed
  5. General Audit - Comprehensive review of current SEO health
""")

    try:
        goal = input("Enter the number or describe your goal (or press Enter for general audit): ").strip()
        return goal if goal else "5"
    except (KeyboardInterrupt, EOFError):
        return "5"


def main():
    """Main entry point for the SEO Audit Agent CLI."""
    parser = argparse.ArgumentParser(
        description="SEO Audit Agent - Comprehensive Technical SEO Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com
  %(prog)s https://example.com --format json --output report.json
  %(prog)s https://example.com --skip-goal
  %(prog)s https://example.com --no-colors

For more information, visit: https://github.com/seo-audit-agent
        """
    )

    parser.add_argument(
        'url',
        help='The URL to audit'
    )

    parser.add_argument(
        '-f', '--format',
        choices=['console', 'json', 'markdown'],
        default='console',
        help='Output format (default: console)'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file path (default: stdout)'
    )

    parser.add_argument(
        '--no-colors',
        action='store_true',
        help='Disable colored output'
    )

    parser.add_argument(
        '--skip-goal',
        action='store_true',
        help='Skip the goal clarification question'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )

    parser.add_argument(
        '--no-verify-ssl',
        action='store_true',
        help='Disable SSL certificate verification'
    )

    parser.add_argument(
        '--skip-crawlability',
        action='store_true',
        help='Skip crawlability analysis'
    )

    parser.add_argument(
        '--skip-performance',
        action='store_true',
        help='Skip performance analysis'
    )

    parser.add_argument(
        '--skip-security',
        action='store_true',
        help='Skip security analysis'
    )

    parser.add_argument(
        '--skip-structured-data',
        action='store_true',
        help='Skip structured data analysis'
    )

    parser.add_argument(
        '--skip-links',
        action='store_true',
        help='Skip link analysis'
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version='SEO Audit Agent v1.0.0'
    )

    args = parser.parse_args()

    # Print banner (unless quiet mode or non-console output)
    if not args.quiet and args.format == 'console' and not args.output:
        print_banner()

    # Get user's goal (unless skipped)
    user_goal = None
    if not args.skip_goal and args.format == 'console' and not args.output:
        user_goal = get_user_goal()

    # Create the agent
    agent = SEOAuditAgent(
        timeout=args.timeout,
        verify_ssl=not args.no_verify_ssl,
    )

    # Progress message
    if not args.quiet:
        print(f"\nAnalyzing: {args.url}")
        print("This may take a moment...\n")

    try:
        # Run the audit
        report = agent.audit(
            url=args.url,
            include_crawlability=not args.skip_crawlability,
            include_page_analysis=True,
            include_performance=not args.skip_performance,
            include_security=not args.skip_security,
            include_structured_data=not args.skip_structured_data,
            include_links=not args.skip_links,
        )

        # Check for fetch errors
        if 'fetch_error' in report.summary_data:
            print(f"\nError: Could not fetch the URL")
            print(f"Details: {report.summary_data['fetch_error']}")
            sys.exit(1)

        # Generate the report
        use_colors = not args.no_colors and args.format == 'console' and not args.output
        output = agent.generate_report(
            report=report,
            format=args.format,
            use_colors=use_colors,
        )

        # Add goal-specific recommendations
        if user_goal and args.format == 'console':
            goal_recommendations = agent.get_goal_recommendations(user_goal)
            output += f"\n{'=' * 70}\n"
            output += goal_recommendations

        # Output results
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            if not args.quiet:
                print(f"Report saved to: {args.output}")
        else:
            print(output)

    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nAudit cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
