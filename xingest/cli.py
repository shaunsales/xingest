"""Command-line interface for xingest."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from xingest import Scraper, ScraperConfig, save_json, __version__
from xingest.config import CacheBackend, LogFormat

app = typer.Typer(
    name="xingest",
    help="X/Twitter profile scraper",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"xingest version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """xingest - X/Twitter profile scraper."""
    pass


@app.command()
def scrape(
    usernames: list[str] = typer.Argument(..., help="Twitter usernames to scrape"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output directory for JSON files"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force refresh, skip cache"
    ),
    headless: bool = typer.Option(
        True, "--headless/--no-headless", help="Run browser in headless mode"
    ),
    delay: int = typer.Option(
        1000, "--delay", "-d", help="Delay between requests in ms"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress output, only show errors"
    ),
):
    """Scrape one or more X/Twitter profiles."""
    config = ScraperConfig(
        headless=headless,
        request_delay_ms=delay,
        log_format=LogFormat.CONSOLE if not quiet else LogFormat.JSON,
    )

    async def run():
        async with Scraper(config) as scraper:
            results = await scraper.scrape_many(usernames, force_refresh=force)

            for result in results:
                if result.success and result.profile:
                    if not quiet:
                        _print_result(result)

                    if output:
                        filepath = output / f"{result.profile.username}.json"
                        save_json(result, filepath)
                        console.print(f"[dim]Saved to {filepath}[/dim]")
                else:
                    console.print(
                        f"[red]✗[/red] Failed to scrape {result.username}: {result.error_message or 'Unknown error'}"
                    )

            # Summary
            success_count = sum(1 for r in results if r.success)
            console.print(f"\n[bold]Scraped {success_count}/{len(results)} profiles[/bold]")

    asyncio.run(run())


@app.command()
def info(
    username: str = typer.Argument(..., help="Twitter username"),
    headless: bool = typer.Option(True, "--headless/--no-headless"),
):
    """Show profile info for a single user."""
    config = ScraperConfig(headless=headless)

    async def run():
        async with Scraper(config) as scraper:
            result = await scraper.scrape(username)

            if result.success and result.profile:
                _print_profile_table(result)
            else:
                console.print(f"[red]Failed to fetch profile: {result.error_message}[/red]")
                raise typer.Exit(1)

    asyncio.run(run())


@app.command()
def cache(
    action: str = typer.Argument(..., help="Action: clear, info"),
    username: Optional[str] = typer.Option(None, "--user", "-u", help="Username to invalidate"),
):
    """Manage the scrape cache."""
    config = ScraperConfig()

    async def run():
        async with Scraper(config) as scraper:
            if action == "clear":
                if username:
                    await scraper.invalidate_cache(username)
                    console.print(f"[green]✓[/green] Cleared cache for @{username}")
                else:
                    await scraper.clear_cache()
                    console.print("[green]✓[/green] Cleared all cache")

            elif action == "info":
                if scraper._cache:
                    cache_path = config.sqlite_path
                    if Path(cache_path).exists():
                        size = Path(cache_path).stat().st_size
                        console.print(f"Cache backend: {config.cache_backend.value}")
                        console.print(f"Cache path: {cache_path}")
                        console.print(f"Cache size: {size / 1024:.1f} KB")
                        console.print(f"TTL: {config.cache_ttl_seconds}s")
                    else:
                        console.print("Cache is empty")
                else:
                    console.print("Cache is disabled")

            else:
                console.print(f"[red]Unknown action: {action}[/red]")
                console.print("Available actions: clear, info")
                raise typer.Exit(1)

    asyncio.run(run())


def _print_result(result):
    """Print scrape result summary."""
    p = result.profile
    cached_tag = "[dim](cached)[/dim]" if result.cached else ""
    
    console.print(f"\n[bold]@{p.username}[/bold] {cached_tag}")
    console.print(f"  {p.display_name or p.username}")
    if p.bio:
        console.print(f"  [dim]{p.bio[:80]}{'...' if len(p.bio) > 80 else ''}[/dim]")
    console.print(f"  [blue]{p.followers_count:,}[/blue] followers · {p.following_count:,} following")
    console.print(f"  [dim]{len(result.tweets)} tweets fetched[/dim]")


def _print_profile_table(result):
    """Print detailed profile as table."""
    p = result.profile

    table = Table(title=f"@{p.username}", show_header=False)
    table.add_column("Field", style="dim")
    table.add_column("Value")

    table.add_row("Display Name", p.display_name or "-")
    table.add_row("Bio", p.bio or "-")
    table.add_row("Followers", f"{p.followers_count:,}")
    table.add_row("Following", f"{p.following_count:,}")
    table.add_row("Verified", "✓" if p.is_verified else "✗")
    table.add_row("Joined", str(p.joined_date.date()) if p.joined_date else "-")
    table.add_row("Website", p.website_url or "-")

    console.print(table)

    if result.tweets:
        console.print(f"\n[bold]Recent Tweets ({len(result.tweets)})[/bold]")
        for tweet in result.tweets[:5]:
            pinned = "[yellow]📌[/yellow] " if tweet.is_pinned else "   "
            text = tweet.text[:60] + "..." if len(tweet.text) > 60 else tweet.text
            console.print(f"{pinned}[dim]{tweet.like_count:>6,}♥[/dim]  {text}")


if __name__ == "__main__":
    app()
