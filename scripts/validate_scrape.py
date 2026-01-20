"""Phase 3 validation script - test live scraping against real accounts."""

import asyncio
import json
from pathlib import Path
from datetime import datetime

from xingest.core.fetcher import fetch_profile_page
from xingest.core.parser import parse_page
from xingest.core.transformer import transform_result

# Test accounts
USERNAMES = [
    "okx",
    "nodepay", 
    "jason",
    "cz_binance",
    "nikitabier",
]

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


async def validate_account(username: str, save_fixture: bool = True) -> dict:
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
    }


async def main():
    """Run validation on all test accounts."""
    print("=" * 60)
    print("PHASE 3: Live Validation")
    print("=" * 60)
    print(f"Testing {len(USERNAMES)} accounts: {', '.join('@' + u for u in USERNAMES)}")
    
    results = []
    for username in USERNAMES:
        result = await validate_account(username)
        results.append(result)
        # Small delay between requests
        await asyncio.sleep(2)
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r.get("success"))
    print(f"\nSuccess: {success_count}/{len(results)}")
    
    print("\n| Username | Profile | Tweets | Duration |")
    print("|----------|---------|--------|----------|")
    for r in results:
        profile = "✓" if r.get("profile_extracted") else "❌"
        tweets = r.get("tweets_count", 0)
        duration = f"{r.get('duration_ms', 0):.0f}ms"
        print(f"| @{r['username']:<8} | {profile:<7} | {tweets:<6} | {duration:<8} |")
    
    print("\nFixtures saved to: tests/fixtures/")


if __name__ == "__main__":
    asyncio.run(main())
