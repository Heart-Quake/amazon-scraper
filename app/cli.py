"""Interface en ligne de commande avec Typer."""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from sqlalchemy import text

import typer
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    # Fallback si rich n'est pas installé
    class Console:
        def print(self, *args, **kwargs): print(*args)
    class Table:
        def __init__(self, *args, **kwargs): pass
        def add_column(self, *args, **kwargs): pass
        def add_row(self, *args, **kwargs): pass
    class Progress:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def add_task(self, *args, **kwargs): return None
        def update(self, *args, **kwargs): pass
        def advance(self, *args, **kwargs): pass
    class SpinnerColumn: pass
    class TextColumn: pass

from app.scrape import AmazonScraper
from app.utils import setup_logging, validate_asin, parse_reviews_url, parse_amazon_url
from app.config import settings
from app.fetch import AmazonFetcher
from app.utils import detect_login_page

# Configuration de l'application Typer
app = typer.Typer(
    name="amazon-scraper",
    help="Scraper d'avis Amazon avec résilience et rotation de proxies",
    no_args_is_help=True,
)

# Console Rich pour l'affichage
console = Console()


@app.command()
def dedupe(
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Afficher ce qui serait supprimé sans toucher à la base"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mode verbeux"),
) -> None:
    """Déduplique la table des avis en conservant un seul enregistrement par contenu équivalent.

    Règle: doublon si (asin, review_title, review_body, review_date) identiques (review_date optionnelle).
    Les entrées avec un review_id Amazon (R...) sont privilégiées par rapport aux review_id générés.
    """
    from app.db import get_db
    from app.models import Review

    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)

    db_gen = get_db()
    db = next(db_gen)
    try:
        # Récupérer toutes les reviews, triées pour garder en priorité celles avec review_id Amazon (R...)
        reviews = (
            db.query(Review)
            .order_by(Review.asin, Review.review_title, Review.review_body, Review.review_date.desc(), Review.review_id.desc())
            .all()
        )

        seen = {}
        to_delete_ids = []

        for r in reviews:
            key = (
                (r.asin or "").strip(),
                (r.review_title or "").strip(),
                (r.review_body or "").strip(),
                (r.review_date or "").strip(),
            )

            current_is_amz = (r.review_id or "").startswith("R")
            if key not in seen:
                seen[key] = r
                continue

            kept = seen[key]
            kept_is_amz = (kept.review_id or "").startswith("R")

            # Choisir lequel garder: prioriser ID Amazon, sinon le plus ancien (created_at)
            keep_current = False
            if current_is_amz and not kept_is_amz:
                keep_current = True
            elif current_is_amz == kept_is_amz and r.created_at and kept.created_at and r.created_at < kept.created_at:
                keep_current = True

            if keep_current:
                to_delete_ids.append(kept.id)
                seen[key] = r
            else:
                to_delete_ids.append(r.id)

        if not to_delete_ids:
            console.print("[green]✓ Aucun doublon détecté[/green]")
            return

        console.print(f"[yellow]Doublons détectés: {len(to_delete_ids)} lignes[/yellow]")
        if dry_run:
            console.print("[blue]Mode dry-run: aucune suppression effectuée. Relancez avec --apply pour nettoyer.[/blue]")
            return

        # Suppression
        deleted = db.query(Review).filter(Review.id.in_(to_delete_ids)).delete(synchronize_session=False)
        db.commit()
        console.print(f"[green]✓ Suppression effectuée: {deleted} lignes supprimées[/green]")

    except Exception as e:
        db.rollback()
        console.print(f"[red]Erreur lors de la déduplication: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()

def crawl(
    asin: str = typer.Argument(..., help="ASIN du produit à scraper"),
    max_pages: Optional[int] = typer.Option(None, "--max-pages", "-p", help="Nombre maximum de pages à scraper"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mode verbeux"),
    url: Optional[str] = typer.Option(None, "--url", help="URL Amazon complète des avis à utiliser comme source"),
    language: Optional[str] = typer.Option(None, "--language", help="Forcer la langue (ex: fr_FR)"),
) -> None:
    """Scrape les avis d'un produit Amazon."""
    # Configuration du logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    
    domain = None
    language = None
    sort = None
    reviewer_type = None
    
    # Si une URL est fournie, on la parse et on en déduit les paramètres
    if url:
        parsed = parse_amazon_url(url)
        if not parsed or not parsed.get("asin"):
            console.print("[red]Erreur: URL d'avis Amazon invalide.[/red]")
            raise typer.Exit(1)
        asin = parsed["asin"]
        domain = parsed.get("domain")
        language = parsed.get("language")
        sort = parsed.get("sort")
        reviewer_type = parsed.get("reviewer_type")
    
    # Validation de l'ASIN (après parse éventuel)
    if not validate_asin(asin):
        console.print(f"[red]Erreur: ASIN invalide '{asin}'. L'ASIN doit contenir exactement 10 caractères alphanumériques.[/red]")
        raise typer.Exit(1)
    
    console.print(f"[blue]Début du scraping pour l'ASIN: {asin}[/blue]")
    
    # Exécution du scraping
    async def run_scraping():
        scraper = AmazonScraper()
        stats = await scraper.scrape_asin(
            asin,
            max_pages,
            domain=domain,
            language=language or language,
            sort=sort,
            reviewer_type=reviewer_type,
        )
        
        # Affichage des résultats
        if stats["success"]:
            console.print(f"[green]✓ Scraping terminé avec succès![/green]")
            console.print(f"  - Avis récupérés: {stats['total_reviews']}")
            console.print(f"  - Pages traitées: {stats['total_pages']}")
        else:
            console.print(f"[red]✗ Scraping terminé avec des erreurs[/red]")
            for error in stats["errors"]:
                console.print(f"  - {error}")
    
    asyncio.run(run_scraping())


@app.command()
def crawl_batch(
    file: Path = typer.Argument(..., help="Fichier contenant les ASINs (un par ligne)"),
    concurrency: int = typer.Option(1, "--concurrency", "-c", help="Niveau de concurrence"),
    max_pages: Optional[int] = typer.Option(None, "--max-pages", "-p", help="Nombre maximum de pages par ASIN"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mode verbeux"),
) -> None:
    """Scrape les avis de plusieurs produits Amazon depuis un fichier."""
    # Configuration du logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    
    # Vérification du fichier
    if not file.exists():
        console.print(f"[red]Erreur: Le fichier '{file}' n'existe pas.[/red]")
        raise typer.Exit(1)
    
    # Lecture des ASINs
    try:
        asins = []
        with open(file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                asin = line.strip()
                if asin and not asin.startswith('#'):  # Ignorer les lignes vides et commentaires
                    if validate_asin(asin):
                        asins.append(asin)
                    else:
                        console.print(f"[yellow]Avertissement: ASIN invalide à la ligne {line_num}: '{asin}'[/yellow]")
        
        if not asins:
            console.print("[red]Erreur: Aucun ASIN valide trouvé dans le fichier.[/red]")
            raise typer.Exit(1)
        
        console.print(f"[blue]Début du scraping en lot de {len(asins)} ASINs[/blue]")
        
    except Exception as e:
        console.print(f"[red]Erreur lors de la lecture du fichier: {e}[/red]")
        raise typer.Exit(1)
    
    # Exécution du scraping en lot
    async def run_batch_scraping():
        scraper = AmazonScraper()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Scraping en cours...", total=len(asins))
            
            results = []
            for i, asin in enumerate(asins):
                progress.update(task, description=f"Traitement de {asin} ({i+1}/{len(asins)})")
                
                try:
                    stats = await scraper.scrape_asin(asin, max_pages)
                    results.append(stats)
                except Exception as e:
                    console.print(f"[red]Erreur pour {asin}: {e}[/red]")
                    results.append({
                        "asin": asin,
                        "total_reviews": 0,
                        "total_pages": 0,
                        "errors": [str(e)],
                        "success": False,
                    })
                
                progress.advance(task)
        
        # Affichage des résultats
        _display_batch_results(results)
    
    asyncio.run(run_batch_scraping())


@app.command()
def export(
    asin: Optional[str] = typer.Option(None, "--asin", "-a", help="ASIN spécifique à exporter"),
    output: str = typer.Option("reviews.csv", "--output", "-o", help="Fichier de sortie"),
    format: str = typer.Option("csv", "--format", "-f", help="Format de sortie (csv, parquet)"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limite du nombre d'avis"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mode verbeux"),
) -> None:
    """Exporte les avis vers un fichier CSV ou Parquet."""
    # Configuration du logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    
    # Validation du format
    if format not in ["csv", "parquet"]:
        console.print("[red]Erreur: Le format doit être 'csv' ou 'parquet'.[/red]")
        raise typer.Exit(1)
    
    # Validation de l'extension du fichier
    output_path = Path(output)
    if format == "csv" and not output_path.suffix.lower() == ".csv":
        output_path = output_path.with_suffix(".csv")
    elif format == "parquet" and not output_path.suffix.lower() == ".parquet":
        output_path = output_path.with_suffix(".parquet")
    
    console.print(f"[blue]Export des avis vers {output_path}[/blue]")
    
    # Récupération des avis
    scraper = AmazonScraper()
    
    if asin:
        if not validate_asin(asin):
            console.print(f"[red]Erreur: ASIN invalide '{asin}'.[/red]")
            raise typer.Exit(1)
        reviews = scraper.get_reviews_for_asin(asin, limit)
        console.print(f"Export de {len(reviews)} avis pour l'ASIN {asin}")
    else:
        reviews = scraper.get_all_reviews(limit)
        console.print(f"Export de {len(reviews)} avis au total")
    
    if not reviews:
        console.print("[yellow]Aucun avis à exporter.[/yellow]")
        return
    
    # Export selon le format
    try:
        if format == "csv":
            _export_to_csv(reviews, output_path)
        else:  # parquet
            _export_to_parquet(reviews, output_path)
        
        console.print(f"[green]✓ Export terminé: {output_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]Erreur lors de l'export: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def health_check(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mode verbeux"),
) -> None:
    """Vérifie l'état du système (DB, Playwright, réseau)."""
    # Configuration du logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    
    console.print("[blue]Vérification de l'état du système...[/blue]")
    
    # Vérification de la base de données
    try:
        from app.db import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        console.print("[green]✓ Base de données: OK[/green]")
    except Exception as e:
        console.print(f"[red]✗ Base de données: Erreur - {e}[/red]")
    
    # Vérification de Playwright
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        console.print("[green]✓ Playwright: OK[/green]")
    except Exception as e:
        console.print(f"[red]✗ Playwright: Erreur - {e}[/red]")
    
    # Vérification du réseau
    try:
        import requests
        response = requests.get("https://www.amazon.fr", timeout=10)
        if response.status_code == 200:
            console.print("[green]✓ Réseau: OK[/green]")
        else:
            console.print(f"[yellow]⚠ Réseau: Code de statut {response.status_code}[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Réseau: Erreur - {e}[/red]")
    
    console.print("[blue]Vérification terminée.[/blue]")


def _display_batch_results(results: List[dict]) -> None:
    """Affiche les résultats du scraping en lot."""
    # Tableau des résultats
    table = Table(title="Résultats du scraping en lot")
    table.add_column("ASIN", style="cyan")
    table.add_column("Avis", justify="right")
    table.add_column("Pages", justify="right")
    table.add_column("Statut", style="green")
    
    total_reviews = 0
    successful = 0
    
    for result in results:
        status = "✓ Succès" if result["success"] else "✗ Erreur"
        status_style = "green" if result["success"] else "red"
        
        table.add_row(
            result["asin"],
            str(result["total_reviews"]),
            str(result["total_pages"]),
            f"[{status_style}]{status}[/{status_style}]",
        )
        
        total_reviews += result["total_reviews"]
        if result["success"]:
            successful += 1
    
    console.print(table)
    console.print(f"\n[blue]Résumé: {total_reviews} avis au total, {successful}/{len(results)} ASINs réussis[/blue]")


def _export_to_csv(reviews: List[dict], output_path: Path) -> None:
    """Exporte les avis vers un fichier CSV."""
    import csv
    
    if not reviews:
        return
    
    # Récupération des colonnes
    columns = list(reviews[0].keys())
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        writer.writeheader()
        writer.writerows(reviews)


def _export_to_parquet(reviews: List[dict], output_path: Path) -> None:
    """Exporte les avis vers un fichier Parquet."""
    import pandas as pd
    
    if not reviews:
        return
    
    df = pd.DataFrame(reviews)
    df.to_parquet(output_path, index=False)


 


@app.command()
def auth_login(
    timeout: int = typer.Option(600, "--timeout", help="Temps max (s) pour finaliser la connexion"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mode verbeux"),
) -> None:
    """Ouvre une fenêtre pour s'authentifier sur Amazon et enregistre la session."""
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)

    console.print("[blue]Ouverture d'une fenêtre Amazon pour authentification...[/blue]")

    async def run_login():
        old_headless = settings.headless
        settings.headless = False
        try:
            fetcher = AmazonFetcher()
            await fetcher.start_browser()
            context = await fetcher.create_context()
            page = await context.new_page()
            
            # 1) Aller à l'accueil FR
            await page.goto("https://www.amazon.fr/", wait_until="domcontentloaded", timeout=settings.timeout_ms)
            # Accepter cookies si présent
            try:
                for sel in [
                    'input#sp-cc-accept',
                    'input[data-cel-widget="sp-cc-accept"]',
                    'input[name="accept"]',
                ]:
                    btn = await page.query_selector(sel)
                    if btn:
                        await btn.click()
                        break
            except Exception:
                pass
            # 2) Cliquer sur le lien "Compte et listes / Identifiez-vous"
            try:
                acc = await page.wait_for_selector('#nav-link-accountList', timeout=8000)
                await acc.click()
                await page.wait_for_load_state("domcontentloaded")
            except Exception:
                # Fallback: URL de signin canonique avec paramètres OpenID
                signin_url = (
                    "https://www.amazon.fr/ap/signin?_encoding=UTF8"
                    "&openid.assoc_handle=frflex"
                    "&openid.return_to=https%3A%2F%2Fwww.amazon.fr%2F%3Fref_%3Dnav_signin"
                    "&openid.mode=checkid_setup&ignoreAuthState=1"
                    "&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
                    "&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select"
                    "&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select"
                )
                await page.goto(signin_url, wait_until="domcontentloaded", timeout=settings.timeout_ms)
            console.print("[yellow]Veuillez vous connecter dans la fenêtre ouverte (2FA si demandé).[/yellow]")

            import time as _time
            start = _time.time()
            logged = False
            while _time.time() - start < timeout:
                try:
                    content = await page.content()
                    if not detect_login_page(content):
                        acc = await page.query_selector('#nav-link-accountList')
                        if acc:
                            txt = (await acc.inner_text()) or ""
                            if "Identifiez-vous" not in txt:
                                logged = True
                                break
                    await page.wait_for_timeout(1500)
                except Exception:
                    await page.wait_for_timeout(1500)
                    continue

            if not logged:
                console.print("[red]Connexion non détectée dans le délai imparti.[/red]")
            else:
                await context.storage_state(path=settings.storage_state_path)
                console.print(f"[green]✓ Session enregistrée: {settings.storage_state_path}[/green]")

            await fetcher.stop_browser()
        finally:
            settings.headless = old_headless

    asyncio.run(run_login())


if __name__ == "__main__":
    app()
