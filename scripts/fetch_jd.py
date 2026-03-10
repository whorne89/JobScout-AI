"""
Playwright-based JD fetcher for JobScout.

Usage:
    python scripts/fetch_jd.py "https://www.linkedin.com/jobs/view/12345/"
    python scripts/fetch_jd.py "https://example.com/job" --timeout 45000
    python scripts/fetch_jd.py "https://example.com/job" --output jd.txt

Outputs full JD text to stdout. Exit code 0 = success, 1 = failure.
Errors/debug info go to stderr.
"""

import sys
import argparse
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def dismiss_overlays(page):
    """Dismiss LinkedIn sign-in modals, cookie banners, and other overlays."""
    dismiss_selectors = [
        # LinkedIn sign-in modal dismiss
        'button[data-tracking-control-name="public_jobs_sign-in-modal_dismiss"]',
        'button.modal__dismiss',
        'button[aria-label="Dismiss"]',
        'button[aria-label="Close"]',
        # Cookie consent
        'button[action-type="ACCEPT"]',
        'button#onetrust-accept-btn-handler',
        'button.artdeco-global-alert__action',
        # Generic close/dismiss buttons on overlays
        'div.modal button.dismiss',
    ]
    for selector in dismiss_selectors:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=500):
                el.click(timeout=1000)
        except Exception:
            pass


def extract_linkedin_jd(page):
    """Extract JD from LinkedIn job page using known selectors."""
    selectors = [
        '.show-more-less-html__markup',
        '.description__text',
        '.jobs-description__content',
        '.jobs-box__html-content',
        'div.description',
        'article.jobs-description',
        # Public LinkedIn job view selectors
        'section.show-more-less-html',
        'div.show-more-less-html__markup--clamp-after-5',
    ]
    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=2000):
                text = el.inner_text(timeout=5000)
                if text and len(text.strip()) > 100:
                    return text.strip()
        except Exception:
            continue
    return None


def extract_greenhouse_jd(page):
    """Extract JD from Greenhouse job pages."""
    selectors = [
        '#content',
        '.content',
        'div#app_body',
        'div.job__description',
        'div.job-post-content',
    ]
    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=2000):
                text = el.inner_text(timeout=5000)
                if text and len(text.strip()) > 100:
                    return text.strip()
        except Exception:
            continue
    return None


def extract_lever_jd(page):
    """Extract JD from Lever job pages."""
    selectors = [
        'div.section-wrapper',
        'div.content',
        'div.posting-page',
    ]
    for selector in selectors:
        try:
            els = page.locator(selector)
            if els.count() > 0:
                texts = []
                for i in range(els.count()):
                    text = els.nth(i).inner_text(timeout=5000)
                    if text:
                        texts.append(text.strip())
                combined = '\n\n'.join(texts)
                if len(combined) > 100:
                    return combined
        except Exception:
            continue
    return None


def extract_generic_jd(page):
    """Fallback: extract full page text and try to isolate JD section."""
    try:
        full_text = page.inner_text('body', timeout=5000)
    except Exception:
        return None

    if not full_text or len(full_text.strip()) < 100:
        return None

    # Try to isolate the JD section by looking for common headers
    jd_markers = [
        r'(?i)about\s+the\s+(job|role|position|opportunity)',
        r'(?i)job\s+description',
        r'(?i)what\s+you\'?ll\s+do',
        r'(?i)responsibilities',
        r'(?i)qualifications',
        r'(?i)requirements',
        r'(?i)who\s+you\s+are',
        r'(?i)what\s+we\'?re\s+looking\s+for',
    ]

    end_markers = [
        r'(?i)apply\s+(now|here|today)',
        r'(?i)equal\s+opportunity\s+employer',
        r'(?i)about\s+us\s*$',
        r'(?i)benefits\s+(&|and)\s+perks',
        r'(?i)similar\s+jobs',
        r'(?i)people\s+also\s+viewed',
        r'(?i)sign\s+in\s+to\s+apply',
    ]

    lines = full_text.split('\n')

    # Find first JD marker
    start_idx = 0
    for i, line in enumerate(lines):
        for marker in jd_markers:
            if re.search(marker, line):
                start_idx = i
                break
        if start_idx > 0:
            break

    # Find end marker after start
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        for marker in end_markers:
            if re.search(marker, lines[i]):
                end_idx = i
                break
        if end_idx < len(lines):
            break

    extracted = '\n'.join(lines[start_idx:end_idx]).strip()

    # If extraction is too thin, return full text (let the pipeline decide)
    if len(extracted) < 100:
        return full_text.strip()

    return extracted


def get_external_apply_url(page):
    """Check if LinkedIn page has an external apply link."""
    selectors = [
        'a.apply-button',
        'a[data-tracking-control-name="public_jobs_apply-link-offsite_sign-in-modal"]',
        'a.sign-in-modal__outlet-btn',
        'a.topcard__link--apply',
    ]
    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=1000):
                href = el.get_attribute('href')
                if href and 'linkedin.com' not in href:
                    return href
        except Exception:
            continue
    return None


def is_ats_url(url):
    """Check if URL is a known ATS platform."""
    ats_domains = ['greenhouse.io', 'lever.co', 'ashbyhq.com', 'jobs.lever.co',
                   'boards.greenhouse.io', 'apply.workable.com']
    return any(domain in url for domain in ats_domains)


def fetch_jd(url, timeout=30000):
    """Fetch JD from URL using Playwright headless Chromium."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='en-US',
        )
        page = context.new_page()

        try:
            # Navigate to URL
            print(f"Navigating to: {url}", file=sys.stderr)
            page.goto(url, timeout=timeout, wait_until='domcontentloaded')

            # Wait a bit for dynamic content to load
            page.wait_for_timeout(3000)

            # Dismiss overlays
            dismiss_overlays(page)
            page.wait_for_timeout(1000)

            # Try clicking "Show more" on LinkedIn if present
            try:
                show_more = page.locator('button.show-more-less-html__button--more').first
                if show_more.is_visible(timeout=1000):
                    show_more.click(timeout=2000)
                    page.wait_for_timeout(500)
            except Exception:
                pass

            jd_text = None
            source = None

            # Determine extraction strategy based on URL
            is_linkedin = 'linkedin.com' in url
            is_greenhouse = 'greenhouse.io' in url
            is_lever = 'lever.co' in url

            if is_linkedin:
                jd_text = extract_linkedin_jd(page)
                if jd_text:
                    source = 'linkedin-targeted'

                # Try external apply link if LinkedIn extraction was thin
                if not jd_text or len(jd_text) < 200:
                    ext_url = get_external_apply_url(page)
                    if ext_url and is_ats_url(ext_url):
                        print(f"Following external apply link: {ext_url}", file=sys.stderr)
                        page.goto(ext_url, timeout=timeout, wait_until='domcontentloaded')
                        page.wait_for_timeout(2000)
                        dismiss_overlays(page)

                        if 'greenhouse.io' in ext_url:
                            jd_text = extract_greenhouse_jd(page) or jd_text
                        elif 'lever.co' in ext_url:
                            jd_text = extract_lever_jd(page) or jd_text
                        else:
                            jd_text = extract_generic_jd(page) or jd_text
                        if jd_text:
                            source = f'external-ats ({ext_url})'
            elif is_greenhouse:
                jd_text = extract_greenhouse_jd(page)
                if jd_text:
                    source = 'greenhouse-targeted'
            elif is_lever:
                jd_text = extract_lever_jd(page)
                if jd_text:
                    source = 'lever-targeted'

            # Generic fallback for any site
            if not jd_text or len(jd_text) < 100:
                jd_text = extract_generic_jd(page)
                if jd_text:
                    source = 'generic-fallback'

            if jd_text and len(jd_text.strip()) >= 100:
                print(f"Extracted {len(jd_text)} chars via {source}", file=sys.stderr)
                return jd_text.strip()
            else:
                print(f"Extraction failed or too thin ({len(jd_text) if jd_text else 0} chars)", file=sys.stderr)
                return None

        except PlaywrightTimeout:
            print(f"Timeout after {timeout}ms", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return None
        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser(description='Fetch job description using Playwright')
    parser.add_argument('url', help='URL of the job posting')
    parser.add_argument('--timeout', type=int, default=30000, help='Navigation timeout in ms (default: 30000)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    args = parser.parse_args()

    result = fetch_jd(args.url, timeout=args.timeout)

    if result:
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"Written to {args.output}", file=sys.stderr)
        else:
            print(result)
        sys.exit(0)
    else:
        print("Failed to extract JD", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
