"""
Integration tests - live scraping against real X/Twitter accounts.

These tests require internet and should be run sparingly to avoid rate limiting.

Run with: pytest tests/test_integration_scrape.py -v
Or standalone: python tests/test_integration_scrape.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

import pytest

from xingest.core.fetcher import fetch_profile_page
from xingest.core.parser import parse_page
from xingest.core.transformer import transform_result

# Mark all tests in this module as integration tests (slow, requires internet)
pytestmark = pytest.mark.integration

# Test accounts - dict with username and expected pinned tweet ID (if known)
TEST_ACCOUNTS = {
    "okx": {"pinned_tweet_id": "2012952460877607151"},  # "Five straight wins" tweet
    "nodepay": {"pinned_tweet_id": None},
    "jason": {"pinned_tweet_id": None},
    "cz_binance": {"pinned_tweet_id": None},
    "nikitabier": {"pinned_tweet_id": None},
}

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class ValidationError(Exception):
    """Raised when validation checks fail."""
    pass


def validate_tweet_data(tweets: list, expected_pinned_id: str | None, username: str) -> list[str]:
    """
    Validate tweet data meets requirements.
    
    Returns list of validation errors (empty if all pass).
    """
    errors = []
    
    if not tweets:
        errors.append("No tweets extracted")
        return errors
    
    # Check all tweets have created_at timestamp
    tweets_missing_timestamp = []
    for t in tweets:
        if t.created_at is None:
            tweets_missing_timestamp.append(t.tweet_id)
    
    if tweets_missing_timestamp:
        errors.append(f"CRITICAL: {len(tweets_missing_timestamp)} tweets missing created_at: {tweets_missing_timestamp[:3]}...")
    
    # Check pinned tweet detection
    pinned_tweets = [t for t in tweets if t.is_pinned]
    
    if expected_pinned_id:
        if not pinned_tweets:
            errors.append(f"CRITICAL: Expected pinned tweet {expected_pinned_id} but none detected")
        elif pinned_tweets[0].tweet_id != expected_pinned_id:
            errors.append(f"CRITICAL: Expected pinned tweet {expected_pinned_id} but got {pinned_tweets[0].tweet_id}")
    
    if len(pinned_tweets) > 1:
        errors.append(f"WARNING: Multiple pinned tweets detected: {[t.tweet_id for t in pinned_tweets]}")
    
    return errors


async def validate_account(username: str, expected: dict, save_fixture: bool = True) -> dict:
    """Scrape and validate a single account."""
    print(f"\n{'='*60}")
    print(f"Scraping @{username}...")
    print(f"{'='*60}")
    
    start = datetime.now()
    
    # Fetch
    try:
        result = await fetch_profile_page(username, headless=True)
        if not result.success:
            print(f"❌ Fetch failed: {result.error}")
            return {"username": username, "success": False, "error": result.error}
    except Exception as e:
        print(f"❌ Fetch exception: {e}")
        return {"username": username, "success": False, "error": str(e)}
    
    duration_ms = (datetime.now() - start).total_seconds() * 1000
    print(f"✓ Fetched in {duration_ms:.0f}ms ({len(result.html)} bytes)")
    
    # Save raw HTML fixture
    if save_fixture:
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        fixture_path = FIXTURES_DIR / f"{username}.html"
        fixture_path.write_text(result.html, encoding="utf-8")
        print(f"✓ Saved fixture: {fixture_path}")
    
    # Parse
    parse_result = parse_page(result.html, username)
    
    # Transform
    scrape_result = transform_result(
        parse_result,
        username=username,
        duration_ms=duration_ms,
    )
    
    # Report findings
    print(f"\n--- Profile Data ---")
    if scrape_result.profile:
        p = scrape_result.profile
        print(f"  Username: @{p.username}")
        print(f"  Display Name: {p.display_name}")
        print(f"  Bio: {p.bio[:80] + '...' if p.bio and len(p.bio) > 80 else p.bio}")
        print(f"  Followers: {p.followers_count:,}")
        print(f"  Following: {p.following_count:,}")
        print(f"  Verified: {p.is_verified}")
        print(f"  Joined: {p.joined_date}")
    else:
        print("  ❌ No profile data extracted!")
    
    print(f"\n--- Tweets ({len(scrape_result.tweets)} found) ---")
    for i, t in enumerate(scrape_result.tweets[:3]):  # Show first 3
        print(f"  [{i+1}] ID: {t.tweet_id}")
        print(f"      Text: {t.text[:60] + '...' if len(t.text) > 60 else t.text}")
        print(f"      Created: {t.created_at}")
        print(f"      Likes: {t.like_count:,} | Reposts: {t.repost_count:,} | Replies: {t.reply_count:,}")
        print(f"      Pinned: {t.is_pinned}")
    
    if len(scrape_result.tweets) > 3:
        print(f"  ... and {len(scrape_result.tweets) - 3} more tweets")
    
    if not scrape_result.tweets:
        print("  ⚠️  No tweets extracted!")
    
    # Parse errors
    if parse_result.parse_errors:
        print(f"\n--- Parse Errors ---")
        for err in parse_result.parse_errors:
            print(f"  ⚠️  {err}")
    
    # Run validation checks
    validation_errors = validate_tweet_data(
        scrape_result.tweets,
        expected.get("pinned_tweet_id"),
        username
    )
    
    if validation_errors:
        print(f"\n--- ❌ VALIDATION ERRORS ---")
        for err in validation_errors:
            print(f"  {err}")
    else:
        print(f"\n--- ✓ All validation checks passed ---")
    
    # Save JSON result
    if save_fixture:
        json_path = FIXTURES_DIR / f"{username}.json"
        json_path.write_text(
            scrape_result.model_dump_json(indent=2),
            encoding="utf-8"
        )
        print(f"\n✓ Saved JSON: {json_path}")
    
    return {
        "username": username,
        "success": scrape_result.success,
        "profile_extracted": scrape_result.profile is not None,
        "tweets_count": len(scrape_result.tweets),
        "duration_ms": duration_ms,
        "validation_errors": validation_errors,
    }


async def main():
    """Run validation on all test accounts."""
    print("=" * 60)
    print("PHASE 3: Live Validation")
    print("=" * 60)
    usernames = list(TEST_ACCOUNTS.keys())
    print(f"Testing {len(usernames)} accounts: {', '.join('@' + u for u in usernames)}")
    
    results = []
    for username, expected in TEST_ACCOUNTS.items():
        result = await validate_account(username, expected)
        results.append(result)
        # Small delay between requests
        await asyncio.sleep(2)
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r.get("success"))
    validation_pass_count = sum(1 for r in results if not r.get("validation_errors"))
    
    print(f"\nScrape Success: {success_count}/{len(results)}")
    print(f"Validation Pass: {validation_pass_count}/{len(results)}")
    
    print("\n| Username    | Profile | Tweets | Validation | Duration |")
    print("|-------------|---------|--------|------------|----------|")
    for r in results:
        profile = "✓" if r.get("profile_extracted") else "❌"
        tweets = r.get("tweets_count", 0)
        val_status = "✓" if not r.get("validation_errors") else "❌"
        duration = f"{r.get('duration_ms', 0):.0f}ms"
        print(f"| @{r['username']:<10} | {profile:<7} | {tweets:<6} | {val_status:<10} | {duration:<8} |")
    
    # Report all validation errors
    all_errors = []
    for r in results:
        for err in r.get("validation_errors", []):
            all_errors.append(f"@{r['username']}: {err}")
    
    if all_errors:
        print(f"\n{'='*60}")
        print("❌ VALIDATION FAILURES")
        print("="*60)
        for err in all_errors:
            print(f"  {err}")
        print(f"\nFixtures saved to: tests/fixtures/")
        sys.exit(1)
    else:
        print(f"\n✅ All validation checks passed!")
        print(f"\nFixtures saved to: tests/fixtures/")


if __name__ == "__main__":
    asyncio.run(main())
