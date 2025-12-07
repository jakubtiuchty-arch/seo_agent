"""
Performance Analyzer - Checks site speed, Core Web Vitals, and resource optimization.
"""

import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from .base import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity, IssueCategory
from ..utils import format_bytes


class PerformanceAnalyzer(BaseAnalyzer):
    """Analyzer for performance-related SEO issues."""

    name = "performance"

    # Resource size thresholds
    MAX_HTML_SIZE = 100 * 1024  # 100KB
    MAX_INLINE_CSS_SIZE = 50 * 1024  # 50KB
    MAX_INLINE_JS_SIZE = 50 * 1024  # 50KB

    def __init__(self, url: str, html_content: str, response_headers: Dict[str, str],
                 response_time: Optional[float] = None, page_size: Optional[int] = None):
        super().__init__(url, html_content, response_headers)
        self.soup = BeautifulSoup(html_content, 'lxml')
        self.response_time = response_time  # in milliseconds
        self.page_size = page_size or len(html_content.encode('utf-8'))

    def analyze(self) -> AnalysisResult:
        """Perform performance analysis."""
        try:
            self._check_response_time()
            self._check_page_size()
            self._check_render_blocking_resources()
            self._check_image_optimization()
            self._check_lazy_loading()
            self._check_compression()
            self._check_caching_headers()
            self._check_preload_preconnect()
            self._check_inline_resources()
            self._analyze_resource_hints()
            # Core Web Vitals specific checks
            self._check_lcp_elements()
            self._check_cls_indicators()
            self._check_fid_indicators()
            self._check_font_display()
            self.result.success = True
        except Exception as e:
            self.result.success = False
            self.result.error = str(e)

        return self.result

    def _check_response_time(self) -> None:
        """Check server response time (TTFB)."""
        if self.response_time is None:
            return

        self.result.data['response_time_ms'] = self.response_time

        if self.response_time > 600:
            self.result.add_issue(SEOIssue(
                title="Slow Server Response Time (TTFB)",
                description=f"Server response time is {self.response_time:.0f}ms. Google recommends under 200ms.",
                severity=IssueSeverity.CRITICAL if self.response_time > 1000 else IssueSeverity.IMPORTANT,
                category=IssueCategory.PERFORMANCE,
                impact="Slow TTFB directly impacts Core Web Vitals (LCP) and user experience. Every 100ms delay can reduce conversions.",
                fix_steps=[
                    "Analyze server-side code for bottlenecks",
                    "Implement server-side caching (Redis, Memcached)",
                    "Optimize database queries and add indexes",
                    "Use a CDN to serve content closer to users",
                    "Upgrade hosting if server resources are insufficient",
                    "Enable HTTP/2 or HTTP/3 for faster connections"
                ],
                expected_outcome="Faster initial server response, improving LCP and overall page load time.",
                validation_steps=[
                    "Use WebPageTest or Lighthouse to measure TTFB",
                    "Monitor TTFB in Google Search Console Core Web Vitals report",
                    "Test from multiple geographic locations"
                ],
                current_value=f"{self.response_time:.0f}ms",
                recommended_value="Under 200ms",
                difficulty="hard",
                priority_score=85 if self.response_time > 1000 else 70
            ))

    def _check_page_size(self) -> None:
        """Check total page size."""
        self.result.data['page_size'] = self.page_size

        if self.page_size > self.MAX_HTML_SIZE:
            self.result.add_issue(SEOIssue(
                title="Large HTML Document Size",
                description=f"HTML document is {format_bytes(self.page_size)}, which may impact load time.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PERFORMANCE,
                impact="Large HTML documents take longer to download and parse, especially on slow connections.",
                fix_steps=[
                    "Enable HTML minification to remove whitespace and comments",
                    "Remove unused HTML elements and code",
                    "Consider lazy loading for below-the-fold content",
                    "Implement pagination for long content",
                    "Move large inline data to external files"
                ],
                expected_outcome="Faster HTML download and parsing, improving First Contentful Paint.",
                validation_steps=[
                    "Check document size in browser DevTools Network tab",
                    "Run Lighthouse audit for performance metrics"
                ],
                current_value=format_bytes(self.page_size),
                recommended_value=f"Under {format_bytes(self.MAX_HTML_SIZE)}",
                difficulty="medium",
                priority_score=55
            ))

    def _check_render_blocking_resources(self) -> None:
        """Check for render-blocking CSS and JavaScript."""
        # Find blocking CSS
        blocking_css = []
        stylesheets = self.soup.find_all('link', attrs={'rel': 'stylesheet'})
        for css in stylesheets:
            media = css.get('media', 'all')
            if media in ['all', 'screen', ''] and not css.get('disabled'):
                href = css.get('href', '')
                if href:
                    blocking_css.append(href)

        # Find blocking JS
        blocking_js = []
        scripts = self.soup.find_all('script', src=True)
        for script in scripts:
            if not script.get('async') and not script.get('defer'):
                src = script.get('src', '')
                if src and not src.startswith('data:'):
                    blocking_js.append(src)

        self.result.data['blocking_resources'] = {
            'css': blocking_css[:10],
            'js': blocking_js[:10],
            'css_count': len(blocking_css),
            'js_count': len(blocking_js)
        }

        if len(blocking_css) > 3:
            self.result.add_issue(SEOIssue(
                title="Multiple Render-Blocking Stylesheets",
                description=f"Found {len(blocking_css)} render-blocking CSS files that delay page rendering.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PERFORMANCE,
                impact="Render-blocking CSS delays First Contentful Paint (FCP) and can hurt Core Web Vitals.",
                fix_steps=[
                    "Inline critical above-the-fold CSS in <head>",
                    "Load non-critical CSS asynchronously",
                    "Use media queries to defer non-essential stylesheets",
                    "Combine and minify CSS files",
                    "Example async load: <link rel='preload' href='styles.css' as='style' onload=\"this.onload=null;this.rel='stylesheet'\">"
                ],
                expected_outcome="Faster initial render and improved FCP/LCP metrics.",
                validation_steps=[
                    "Run Lighthouse and check 'Eliminate render-blocking resources'",
                    "Use Chrome DevTools Coverage to find unused CSS"
                ],
                current_value=f"{len(blocking_css)} blocking stylesheets",
                recommended_value="1-2 critical stylesheets",
                affected_elements=[css[:80] for css in blocking_css[:5]],
                difficulty="medium",
                priority_score=65
            ))

        if len(blocking_js) > 2:
            self.result.add_issue(SEOIssue(
                title="Render-Blocking JavaScript",
                description=f"Found {len(blocking_js)} render-blocking scripts without async or defer.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PERFORMANCE,
                impact="Blocking scripts halt HTML parsing, significantly delaying page render.",
                fix_steps=[
                    "Add 'defer' attribute to scripts that don't need immediate execution",
                    "Add 'async' attribute to independent scripts (analytics, ads)",
                    "Move non-critical scripts to the end of <body>",
                    "Example: <script src='app.js' defer></script>",
                    "Use dynamic imports for non-essential JavaScript"
                ],
                expected_outcome="Faster page rendering as HTML parsing isn't blocked by scripts.",
                validation_steps=[
                    "Check all <script> tags have async or defer where appropriate",
                    "Run Lighthouse to verify render-blocking scripts are resolved"
                ],
                current_value=f"{len(blocking_js)} blocking scripts",
                recommended_value="All non-critical scripts should be async or defer",
                affected_elements=[js[:80] for js in blocking_js[:5]],
                difficulty="medium",
                priority_score=70
            ))

    def _check_image_optimization(self) -> None:
        """Check image optimization opportunities."""
        images = self.soup.find_all('img')

        large_images = []
        non_modern_formats = []
        missing_srcset = []

        for img in images:
            src = img.get('src', img.get('data-src', ''))
            if not src or src.startswith('data:'):
                continue

            # Check for modern formats
            src_lower = src.lower()
            if any(ext in src_lower for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                non_modern_formats.append(src[:80])

            # Check for responsive images
            if not img.get('srcset') and not img.parent.name == 'picture':
                missing_srcset.append(src[:80])

        self.result.data['image_optimization'] = {
            'total_images': len(images),
            'non_modern_formats': len(non_modern_formats),
            'missing_srcset': len(missing_srcset)
        }

        if non_modern_formats:
            self.result.add_issue(SEOIssue(
                title="Images Not Using Modern Formats",
                description=f"{len(non_modern_formats)} images use older formats (JPG, PNG, GIF) instead of modern formats.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Modern formats like WebP and AVIF offer 25-50% better compression with same quality.",
                fix_steps=[
                    "Convert images to WebP format for broad support",
                    "Consider AVIF for even better compression (newer browsers)",
                    "Use <picture> element for format fallbacks:",
                    "  <picture>",
                    "    <source srcset='image.avif' type='image/avif'>",
                    "    <source srcset='image.webp' type='image/webp'>",
                    "    <img src='image.jpg' alt='...'>",
                    "  </picture>",
                    "Use automatic image CDN services (Cloudinary, imgix)"
                ],
                expected_outcome="Significant reduction in image file sizes, improving LCP and page load time.",
                validation_steps=[
                    "Check Network tab for image formats",
                    "Run Lighthouse for 'Serve images in modern formats'",
                    "Verify WebP/AVIF images are being served"
                ],
                current_value=f"{len(non_modern_formats)} images in old formats",
                recommended_value="Use WebP or AVIF",
                affected_elements=non_modern_formats[:5],
                difficulty="medium",
                priority_score=45
            ))

        if len(missing_srcset) > 3:
            self.result.add_issue(SEOIssue(
                title="Images Missing Responsive Srcset",
                description=f"{len(missing_srcset)} images don't use srcset for responsive loading.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Without srcset, mobile users download full-size images, wasting bandwidth.",
                fix_steps=[
                    "Add srcset attribute with multiple image sizes",
                    "Add sizes attribute to guide browser selection",
                    "Example:",
                    "  <img srcset='small.jpg 480w, medium.jpg 800w, large.jpg 1200w'",
                    "       sizes='(max-width: 600px) 480px, 800px'",
                    "       src='medium.jpg' alt='...'>",
                    "Use responsive image generators or CDN auto-sizing"
                ],
                expected_outcome="Appropriate image sizes served based on device, saving bandwidth.",
                validation_steps=[
                    "Verify srcset appears on major images",
                    "Test on mobile to confirm smaller images load"
                ],
                current_value=f"{len(missing_srcset)} images without srcset",
                affected_elements=missing_srcset[:5],
                difficulty="medium",
                priority_score=35
            ))

    def _check_lazy_loading(self) -> None:
        """Check for lazy loading implementation."""
        images = self.soup.find_all('img')
        iframes = self.soup.find_all('iframe')

        images_not_lazy = []
        iframes_not_lazy = []

        for img in images:
            loading = img.get('loading')
            # Skip small images or icons that shouldn't be lazy loaded
            if not loading or loading != 'lazy':
                src = img.get('src', '')
                if src and not src.startswith('data:') and not 'icon' in src.lower():
                    images_not_lazy.append(src[:80])

        for iframe in iframes:
            loading = iframe.get('loading')
            if not loading or loading != 'lazy':
                src = iframe.get('src', '')[:80]
                iframes_not_lazy.append(src)

        self.result.data['lazy_loading'] = {
            'images_not_lazy': len(images_not_lazy),
            'iframes_not_lazy': len(iframes_not_lazy)
        }

        # Only flag if there are multiple images that could benefit
        if len(images_not_lazy) > 5:
            self.result.add_issue(SEOIssue(
                title="Images Missing Lazy Loading",
                description=f"{len(images_not_lazy)} images don't use native lazy loading.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Without lazy loading, all images load immediately, delaying initial page render.",
                fix_steps=[
                    "Add loading='lazy' to images below the fold",
                    "Example: <img src='image.jpg' loading='lazy' alt='...'>",
                    "Don't lazy load above-the-fold images (hero images)",
                    "Consider using loading='eager' for critical images",
                    "Native lazy loading is supported in all modern browsers"
                ],
                expected_outcome="Faster initial page load by deferring off-screen images.",
                validation_steps=[
                    "Check img tags for loading='lazy' attribute",
                    "Use Network tab to verify images load as you scroll"
                ],
                current_value=f"{len(images_not_lazy)} images without lazy loading",
                difficulty="easy",
                priority_score=40
            ))

        if len(iframes_not_lazy) > 0:
            self.result.add_issue(SEOIssue(
                title="Iframes Missing Lazy Loading",
                description=f"{len(iframes_not_lazy)} iframes could benefit from lazy loading.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Iframes (especially videos, maps, embeds) can significantly impact page load if not lazy loaded.",
                fix_steps=[
                    "Add loading='lazy' to iframe elements",
                    "Example: <iframe src='...' loading='lazy'></iframe>",
                    "Use facade patterns for YouTube/Vimeo embeds"
                ],
                expected_outcome="Faster initial load by deferring heavy iframe content.",
                validation_steps=[
                    "Check iframe tags for loading='lazy'",
                    "Verify iframes load only when scrolled into view"
                ],
                current_value=f"{len(iframes_not_lazy)} iframes without lazy loading",
                affected_elements=iframes_not_lazy[:3],
                difficulty="easy",
                priority_score=35
            ))

    def _check_compression(self) -> None:
        """Check if compression is enabled."""
        content_encoding = self.response_headers.get('Content-Encoding', '').lower()

        self.result.data['compression'] = {
            'enabled': content_encoding in ['gzip', 'br', 'deflate'],
            'type': content_encoding if content_encoding else None
        }

        if content_encoding not in ['gzip', 'br', 'deflate']:
            self.result.add_issue(SEOIssue(
                title="Text Compression Not Enabled",
                description="Response is not using gzip, Brotli, or deflate compression.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PERFORMANCE,
                impact="Uncompressed text resources are 60-80% larger than compressed, significantly slowing downloads.",
                fix_steps=[
                    "Enable Brotli compression (best compression ratio)",
                    "Or enable gzip compression (wider support)",
                    "Apache: Add to .htaccess or enable mod_deflate",
                    "Nginx: Add gzip on; and gzip_types in config",
                    "Use CDN compression (Cloudflare, CloudFront)",
                    "Verify compression for HTML, CSS, JS, SVG, JSON"
                ],
                expected_outcome="60-80% reduction in text resource sizes, faster page loads.",
                validation_steps=[
                    "Check Response Headers for 'Content-Encoding: gzip' or 'br'",
                    "Use online compression testers",
                    "Run Lighthouse 'Enable text compression' audit"
                ],
                recommended_value="gzip or br (Brotli)",
                difficulty="medium",
                priority_score=75
            ))

    def _check_caching_headers(self) -> None:
        """Check caching headers for proper configuration."""
        cache_control = self.response_headers.get('Cache-Control', '')
        expires = self.response_headers.get('Expires', '')
        etag = self.response_headers.get('ETag', '')

        self.result.data['caching'] = {
            'cache_control': cache_control,
            'expires': expires,
            'etag': bool(etag)
        }

        has_caching = cache_control or expires

        if not has_caching:
            self.result.add_issue(SEOIssue(
                title="Missing Cache Headers",
                description="No Cache-Control or Expires headers found for this page.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Without caching headers, browsers may re-download resources unnecessarily on repeat visits.",
                fix_steps=[
                    "Add Cache-Control header for HTML pages:",
                    "  Cache-Control: public, max-age=300 (5 minutes for dynamic)",
                    "For static assets (CSS, JS, images):",
                    "  Cache-Control: public, max-age=31536000, immutable",
                    "Use versioned filenames for cache busting",
                    "Configure caching in your web server or CDN"
                ],
                expected_outcome="Faster repeat visits as resources are served from browser cache.",
                validation_steps=[
                    "Check Response Headers for Cache-Control",
                    "Verify assets have long cache times",
                    "Use browser DevTools to check 'from cache' responses"
                ],
                recommended_value="Cache-Control: public, max-age=...",
                difficulty="medium",
                priority_score=45
            ))
        elif 'no-store' in cache_control or 'no-cache' in cache_control:
            self.result.add_issue(SEOIssue(
                title="Caching Disabled",
                description=f"Cache-Control header disables caching: {cache_control}",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="With caching disabled, every visit requires full page download.",
                fix_steps=[
                    "Review if no-cache/no-store is intentional",
                    "For public content, consider enabling caching",
                    "Use short max-age for dynamic content that changes frequently"
                ],
                expected_outcome="Improved performance for returning visitors.",
                validation_steps=[
                    "Review Cache-Control header value",
                    "Confirm caching policy matches content needs"
                ],
                current_value=cache_control,
                difficulty="easy",
                priority_score=30
            ))

    def _check_preload_preconnect(self) -> None:
        """Check for resource hints (preload, preconnect)."""
        preloads = self.soup.find_all('link', attrs={'rel': 'preload'})
        preconnects = self.soup.find_all('link', attrs={'rel': 'preconnect'})
        dns_prefetch = self.soup.find_all('link', attrs={'rel': 'dns-prefetch'})

        self.result.data['resource_hints'] = {
            'preloads': len(preloads),
            'preconnects': len(preconnects),
            'dns_prefetch': len(dns_prefetch)
        }

        # Find external resources that could benefit from preconnect
        external_domains = set()
        scripts = self.soup.find_all('script', src=True)
        stylesheets = self.soup.find_all('link', attrs={'rel': 'stylesheet'})

        current_domain = urlparse(self.url).netloc

        for script in scripts:
            src = script.get('src', '')
            if src.startswith('http'):
                domain = urlparse(src).netloc
                if domain and domain != current_domain:
                    external_domains.add(domain)

        for css in stylesheets:
            href = css.get('href', '')
            if href.startswith('http'):
                domain = urlparse(href).netloc
                if domain and domain != current_domain:
                    external_domains.add(domain)

        preconnected_domains = set()
        for pc in preconnects:
            href = pc.get('href', '')
            if href:
                domain = urlparse(href).netloc
                preconnected_domains.add(domain)

        missing_preconnects = external_domains - preconnected_domains

        if len(missing_preconnects) > 2:
            self.result.add_issue(SEOIssue(
                title="Missing Preconnect Hints",
                description=f"Found {len(missing_preconnects)} external domains without preconnect hints.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Preconnect hints can save 100-500ms per external domain by establishing early connections.",
                fix_steps=[
                    "Add preconnect hints for critical external domains:",
                    "  <link rel='preconnect' href='https://domain.com'>",
                    "Also add dns-prefetch as fallback:",
                    "  <link rel='dns-prefetch' href='https://domain.com'>",
                    "Only preconnect to domains used early in page load",
                    "Don't preconnect to too many domains (limit to 4-6)"
                ],
                expected_outcome="Faster connection to external resources, improving load time.",
                validation_steps=[
                    "Check <head> for preconnect links",
                    "Use WebPageTest to verify connection timing"
                ],
                current_value=f"{len(preconnects)} preconnects, {len(missing_preconnects)} missing",
                affected_elements=list(missing_preconnects)[:5],
                difficulty="easy",
                priority_score=30
            ))

    def _check_inline_resources(self) -> None:
        """Check for excessive inline CSS/JS."""
        # Find inline styles
        style_tags = self.soup.find_all('style')
        inline_css_size = sum(len(style.get_text()) for style in style_tags)

        # Find inline scripts
        inline_scripts = self.soup.find_all('script', src=False)
        inline_js_size = sum(len(script.get_text()) for script in inline_scripts
                           if script.get_text().strip())

        self.result.data['inline_resources'] = {
            'css_size': inline_css_size,
            'js_size': inline_js_size,
            'style_tags': len(style_tags),
            'inline_scripts': len(inline_scripts)
        }

        if inline_css_size > self.MAX_INLINE_CSS_SIZE:
            self.result.add_issue(SEOIssue(
                title="Excessive Inline CSS",
                description=f"Found {format_bytes(inline_css_size)} of inline CSS in {len(style_tags)} style tags.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Large inline CSS increases HTML size and can't be cached separately.",
                fix_steps=[
                    "Keep only critical CSS inline (above-the-fold styles)",
                    "Move remaining CSS to external cacheable files",
                    "Limit inline critical CSS to 10-15KB",
                    "Use tools like Critical or Critters to extract critical CSS"
                ],
                expected_outcome="Smaller HTML, cacheable CSS, faster repeat visits.",
                validation_steps=[
                    "Measure inline style size with DevTools",
                    "Verify critical CSS is minimal but functional"
                ],
                current_value=format_bytes(inline_css_size),
                recommended_value=f"Under {format_bytes(self.MAX_INLINE_CSS_SIZE)}",
                difficulty="medium",
                priority_score=30
            ))

        if inline_js_size > self.MAX_INLINE_JS_SIZE:
            self.result.add_issue(SEOIssue(
                title="Excessive Inline JavaScript",
                description=f"Found {format_bytes(inline_js_size)} of inline JavaScript.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Large inline scripts increase HTML size and block parsing.",
                fix_steps=[
                    "Move inline scripts to external files",
                    "External scripts can be cached and loaded async",
                    "Only keep small initialization code inline",
                    "Minify any remaining inline JavaScript"
                ],
                expected_outcome="Smaller HTML, cacheable JS, non-blocking script loading.",
                validation_steps=[
                    "Check for large inline script blocks",
                    "Verify scripts are in external files"
                ],
                current_value=format_bytes(inline_js_size),
                recommended_value=f"Under {format_bytes(self.MAX_INLINE_JS_SIZE)}",
                difficulty="medium",
                priority_score=30
            ))

    def _analyze_resource_hints(self) -> None:
        """Analyze and suggest resource hint optimizations."""
        # Check for preload of critical resources
        preloads = self.soup.find_all('link', attrs={'rel': 'preload'})
        preload_as = [p.get('as') for p in preloads]

        # Look for fonts that should be preloaded
        font_links = self.soup.find_all('link', attrs={'rel': 'stylesheet'})
        has_google_fonts = any('fonts.googleapis.com' in (link.get('href', ''))
                              for link in font_links)

        if has_google_fonts and 'font' not in preload_as:
            self.result.add_issue(SEOIssue(
                title="Font Preloading Opportunity",
                description="Google Fonts detected but fonts are not preloaded.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Font files discovered late in page load can cause FOUT/FOIT and affect LCP.",
                fix_steps=[
                    "Preconnect to Google Fonts domains:",
                    "  <link rel='preconnect' href='https://fonts.googleapis.com'>",
                    "  <link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>",
                    "Or self-host fonts for better performance",
                    "Consider using font-display: swap for visibility"
                ],
                expected_outcome="Faster font loading, reduced layout shifts from fonts.",
                validation_steps=[
                    "Check for preconnect hints to font domains",
                    "Verify fonts load early in waterfall"
                ],
                difficulty="easy",
                priority_score=35
            ))

    def _check_lcp_elements(self) -> None:
        """Check for potential LCP (Largest Contentful Paint) issues."""
        images = self.soup.find_all('img')

        # Check for hero images that might be LCP candidates
        hero_patterns = ['hero', 'banner', 'featured', 'main', 'header-image', 'cover']
        potential_lcp_images = []

        for img in images:
            classes = ' '.join(img.get('class', []))
            img_id = img.get('id', '')
            src = img.get('src', img.get('data-src', ''))

            is_hero = any(pattern in classes.lower() or pattern in img_id.lower()
                         for pattern in hero_patterns)

            if is_hero or (src and not img.get('loading') == 'lazy'):
                potential_lcp_images.append({
                    'src': src[:80] if src else 'no-src',
                    'has_fetchpriority': img.get('fetchpriority') == 'high',
                    'has_srcset': bool(img.get('srcset'))
                })

        preloaded_images = self.soup.find_all('link', attrs={'rel': 'preload', 'as': 'image'})

        self.result.data['lcp_candidates'] = {
            'potential_lcp_images': len(potential_lcp_images),
            'preloaded_images': len(preloaded_images)
        }

        unoptimized_hero = [img for img in potential_lcp_images
                          if not img['has_fetchpriority']]

        if unoptimized_hero and len(unoptimized_hero) <= 5:
            self.result.add_issue(SEOIssue(
                title="LCP Image May Need Optimization",
                description=f"Found {len(unoptimized_hero)} potential LCP images without fetchpriority='high'.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PERFORMANCE,
                impact="The Largest Contentful Paint (LCP) is a Core Web Vital. Hero images should be prioritized for faster LCP.",
                fix_steps=[
                    "Add fetchpriority='high' to your main hero/banner image:",
                    "  <img src='hero.jpg' fetchpriority='high' alt='...'>",
                    "Preload the LCP image:",
                    "  <link rel='preload' as='image' href='hero.jpg'>",
                    "Avoid lazy loading the LCP image",
                    "Ensure the image is served in optimal format (WebP/AVIF)"
                ],
                expected_outcome="Faster LCP times, improved Core Web Vitals score.",
                validation_steps=[
                    "Run PageSpeed Insights and check LCP timing",
                    "Use Chrome DevTools Performance tab to identify LCP element",
                    "Target LCP under 2.5 seconds"
                ],
                recommended_value="fetchpriority='high' on LCP image",
                affected_elements=[img['src'] for img in unoptimized_hero[:5]],
                difficulty="easy",
                priority_score=70
            ))

    def _check_cls_indicators(self) -> None:
        """Check for potential CLS (Cumulative Layout Shift) issues."""
        images = self.soup.find_all('img')
        images_without_dims = []

        for img in images:
            if not (img.get('width') and img.get('height')):
                src = img.get('src', img.get('data-src', ''))[:80]
                if src:
                    images_without_dims.append(src)

        # Check for dynamic content injection points (ads)
        ads_patterns = ['ad-', 'advertisement', 'banner', 'promo', 'sponsor']
        potential_ad_slots = []
        for element in self.soup.find_all(['div', 'section', 'aside']):
            classes = ' '.join(element.get('class', [])).lower()
            element_id = (element.get('id') or '').lower()
            if any(pattern in classes or pattern in element_id for pattern in ads_patterns):
                potential_ad_slots.append(element.name)

        self.result.data['cls_indicators'] = {
            'images_without_dimensions': len(images_without_dims),
            'potential_ad_slots': len(potential_ad_slots)
        }

        if images_without_dims:
            self.result.add_issue(SEOIssue(
                title="Images Causing Layout Shift Risk",
                description=f"{len(images_without_dims)} images lack width/height attributes, risking layout shifts.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PERFORMANCE,
                impact="Images without dimensions cause layout shifts (CLS) when they load, hurting Core Web Vitals.",
                fix_steps=[
                    "Add width and height attributes to all img tags",
                    "Use the image's natural aspect ratio dimensions",
                    "Example: <img src='photo.jpg' width='800' height='600'>",
                    "CSS can still control display size with max-width: 100%",
                    "For responsive images, use CSS aspect-ratio property"
                ],
                expected_outcome="Zero or minimal CLS from images, improved Core Web Vitals.",
                validation_steps=[
                    "Run PageSpeed Insights and check CLS score",
                    "Use Chrome DevTools to identify layout shifts",
                    "Target CLS under 0.1"
                ],
                current_value=f"{len(images_without_dims)} images without dimensions",
                recommended_value="All images should have width/height",
                affected_elements=images_without_dims[:10],
                difficulty="medium",
                priority_score=65
            ))

        if potential_ad_slots:
            self.result.add_issue(SEOIssue(
                title="Ad Slots May Cause Layout Shifts",
                description=f"Found {len(potential_ad_slots)} potential ad containers that may inject content.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Dynamically loaded ads often cause significant layout shifts if space isn't reserved.",
                fix_steps=[
                    "Reserve space for ads with min-height CSS",
                    "Use CSS aspect-ratio to maintain ad slot dimensions",
                    "Example: .ad-slot { min-height: 250px; }",
                    "Consider using CSS contain: layout for ad containers"
                ],
                expected_outcome="Reduced layout shifts from ad loading.",
                validation_steps=[
                    "Monitor CLS in real user monitoring",
                    "Verify ad containers have reserved space"
                ],
                difficulty="medium",
                priority_score=45
            ))

    def _check_fid_indicators(self) -> None:
        """Check for potential FID (First Input Delay) / INP issues."""
        scripts = self.soup.find_all('script')
        external_scripts = [s for s in scripts if s.get('src')]
        inline_scripts = [s for s in scripts if not s.get('src') and s.string]

        total_inline_js = sum(len(s.string) for s in inline_scripts if s.string)

        # Check for heavy third-party scripts
        heavy_third_parties = {
            'analytics': ['google-analytics.com', 'googletagmanager.com'],
            'social': ['facebook.net', 'twitter.com', 'linkedin.com'],
            'ads': ['googlesyndication.com', 'doubleclick.net'],
            'chat': ['intercom', 'drift', 'zendesk', 'crisp'],
            'tracking': ['hotjar', 'fullstory', 'clarity']
        }

        found_third_parties = {category: [] for category in heavy_third_parties}

        for script in external_scripts:
            src = script.get('src', '').lower()
            for category, patterns in heavy_third_parties.items():
                if any(pattern in src for pattern in patterns):
                    found_third_parties[category].append(src[:60])

        total_third_party = sum(len(v) for v in found_third_parties.values())

        self.result.data['fid_indicators'] = {
            'total_scripts': len(scripts),
            'external_scripts': len(external_scripts),
            'inline_js_size': total_inline_js,
            'third_party_count': total_third_party
        }

        if total_third_party > 5:
            all_third_party = []
            for scripts_list in found_third_parties.values():
                all_third_party.extend(scripts_list[:2])

            self.result.add_issue(SEOIssue(
                title="Heavy Third-Party Script Usage",
                description=f"Found {total_third_party} third-party scripts that may impact interactivity.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PERFORMANCE,
                impact="Third-party scripts compete for the main thread, increasing First Input Delay (FID) and Interaction to Next Paint (INP).",
                fix_steps=[
                    "Audit third-party scripts for necessity",
                    "Load non-critical scripts asynchronously or defer them",
                    "Use resource hints: <link rel='preconnect'>",
                    "Consider lazy loading widgets (chat, social) on interaction",
                    "Implement facade patterns for heavy embeds"
                ],
                expected_outcome="Faster interactivity (FID/INP) and better responsiveness.",
                validation_steps=[
                    "Run PageSpeed Insights and check TBT/FID",
                    "Use Chrome DevTools Performance tab",
                    "Monitor real user INP in Search Console"
                ],
                current_value=f"{total_third_party} third-party scripts",
                affected_elements=all_third_party[:6],
                difficulty="medium",
                priority_score=60
            ))

        if total_inline_js > 50000:
            self.result.add_issue(SEOIssue(
                title="Large Inline JavaScript Blocking Main Thread",
                description=f"Found {format_bytes(total_inline_js)} of inline JavaScript that blocks parsing.",
                severity=IssueSeverity.IMPORTANT,
                category=IssueCategory.PERFORMANCE,
                impact="Large inline scripts block HTML parsing and delay interactivity.",
                fix_steps=[
                    "Move inline JavaScript to external files",
                    "Use defer or async for external scripts",
                    "Code-split to load only necessary JS initially",
                    "Use web workers for heavy computations"
                ],
                expected_outcome="Faster time to interactive and improved FID/INP.",
                validation_steps=[
                    "Check Total Blocking Time in Lighthouse",
                    "Profile with DevTools Performance tab"
                ],
                current_value=format_bytes(total_inline_js),
                difficulty="hard",
                priority_score=55
            ))

    def _check_font_display(self) -> None:
        """Check for font-display optimization."""
        style_tags = self.soup.find_all('style')
        has_font_face = False
        has_font_display_swap = False

        for style in style_tags:
            content = style.get_text()
            if '@font-face' in content:
                has_font_face = True
                if 'font-display' in content:
                    has_font_display_swap = True

        font_links = self.soup.find_all('link', attrs={'rel': 'stylesheet'})
        google_fonts_links = [link.get('href', '') for link in font_links
                             if 'fonts.googleapis.com' in link.get('href', '')]

        google_fonts_with_display = [link for link in google_fonts_links if 'display=' in link]

        self.result.data['font_display'] = {
            'has_font_face': has_font_face,
            'has_font_display': has_font_display_swap,
            'google_fonts_count': len(google_fonts_links),
            'google_fonts_with_display': len(google_fonts_with_display)
        }

        if google_fonts_links and len(google_fonts_with_display) < len(google_fonts_links):
            missing_display = len(google_fonts_links) - len(google_fonts_with_display)
            self.result.add_issue(SEOIssue(
                title="Google Fonts Missing display Parameter",
                description=f"{missing_display} Google Fonts link(s) missing the display=swap parameter.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Without font-display: swap, text may be invisible while fonts load (FOIT), hurting LCP.",
                fix_steps=[
                    "Add &display=swap to your Google Fonts URL",
                    "Example: https://fonts.googleapis.com/css2?family=Roboto&display=swap",
                    "Or self-host fonts with font-display: swap in @font-face"
                ],
                expected_outcome="Text visible immediately with fallback font, no invisible text period.",
                validation_steps=[
                    "Check Google Fonts URLs for display parameter",
                    "Throttle network and verify text is visible during load"
                ],
                current_value=f"{missing_display} fonts without display=swap",
                difficulty="easy",
                priority_score=40
            ))

        if has_font_face and not has_font_display_swap:
            self.result.add_issue(SEOIssue(
                title="Custom Fonts Missing font-display",
                description="@font-face declarations found without font-display property.",
                severity=IssueSeverity.RECOMMENDED,
                category=IssueCategory.PERFORMANCE,
                impact="Without font-display, browsers may hide text while loading fonts (FOIT).",
                fix_steps=[
                    "Add font-display: swap to all @font-face rules",
                    "Example: @font-face { font-family: 'MyFont'; font-display: swap; src: url(...); }",
                    "Consider font-display: optional for non-critical fonts"
                ],
                expected_outcome="Text visible immediately with fallback fonts during font loading.",
                validation_steps=[
                    "Review @font-face declarations for font-display",
                    "Test with slow network throttling"
                ],
                recommended_value="font-display: swap",
                difficulty="easy",
                priority_score=35
            ))
