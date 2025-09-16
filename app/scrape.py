"""Module principal de scraping avec pagination et persistance."""

import logging
import importlib
import time
from typing import List, Optional, Callable
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db, create_tables
from app.fetch import AmazonFetcher
from app.models import Review
from app.selectors import ReviewSelectors
from app.utils import async_random_sleep

logger = logging.getLogger(__name__)


class AmazonScraper:
    """Scraper principal pour les avis Amazon."""
    
    def __init__(self):
        """Initialise le scraper avec les composants nécessaires."""
        self.fetcher = AmazonFetcher()
        # Import paresseux pour éviter les erreurs d'import au démarrage de Streamlit
        try:
            parser_module = importlib.import_module("app.parser")
            ReviewParserCls = getattr(parser_module, "ReviewParser")
            self.parser = ReviewParserCls()
        except Exception as e:
            logger.error(f"Impossible d'importer/initialiser ReviewParser: {e}")
            raise
        self.selectors = ReviewSelectors()
        
        # Création des tables si nécessaire
        create_tables()
    
    async def scrape_asin(
        self,
        asin: str,
        max_pages: Optional[int] = None,
        *,
        domain: Optional[str] = None,
        language: Optional[str] = None,
        sort: Optional[str] = None,
        reviewer_type: Optional[str] = None,
        progress_cb: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        """
        Scrape tous les avis d'un ASIN avec pagination.
        
        Args:
            asin: ASIN du produit à scraper
            max_pages: Nombre maximum de pages à scraper (optionnel)
            
        Returns:
            Dictionnaire avec les statistiques de scraping
        """
        from app.config import settings
        
        max_pages = max_pages or settings.max_pages_per_asin
        total_reviews = 0
        total_encountered = 0
        total_duplicates = 0
        total_pages = 0
        errors = []
        pages_details = []
        
        logger.info(f"Début du scraping pour ASIN: {asin} (max {max_pages} pages)")
        
        try:
            async with self.fetcher:
                # Vérifier/établir la connexion avant de commencer le scraping
                try:
                    context = await self.fetcher.create_context()
                    # Si storage_state non présent, ensure_logged_in() se chargera via creds
                    await self.fetcher.ensure_logged_in(context)
                    await context.close()
                except Exception as e:
                    logger.warning(f"Vérification de connexion ignorée/échouée (on continue): {e}")
                page = None
                for page_num in range(1, max_pages + 1):
                    try:
                        logger.info(f"Traitement de la page {page_num}")
                        started_at = time.time()
                        
                        # Récupération / navigation
                        if page is None:
                            page = await self.fetcher.fetch_reviews_page(
                                asin,
                                page_num,
                                domain=domain,
                                language=language,
                                sort=sort,
                                reviewer_type=reviewer_type,
                            )
                        if not page:
                            logger.warning(f"Impossible de récupérer la page {page_num}")
                            break
                        
                        # Parsing des avis
                        try:
                            reviews = await self.parser.parse_reviews_from_page(page)
                        except Exception as e:
                            # Dump de debug si les sélecteurs ne matchent pas (anti-bot / layout nouveau)
                            try:
                                html = await page.content()
                                with open("debug/last_page.html", "w", encoding="utf-8") as f:
                                    f.write(html)
                                try:
                                    await page.screenshot(path="debug/last_page.png", full_page=True)
                                except Exception:
                                    pass
                            except Exception:
                                pass
                            raise e
                        
                        if not reviews:
                            logger.info(f"Aucun avis trouvé sur la page {page_num}, arrêt de la pagination")
                            pages_details.append({
                                "page": page_num,
                                "reviews_parsed": 0,
                                "saved": 0,
                                "duration_s": round(time.time() - started_at, 2),
                                "next": False,
                                "error": None,
                            })
                            break
                        
                        # Ajout de l'ASIN aux avis
                        for review in reviews:
                            review["asin"] = asin
                        
                        # Sauvegarde en base
                        saved_count = await self._save_reviews(reviews)
                        total_reviews += saved_count
                        encountered = len(reviews)
                        dups = max(0, encountered - saved_count)
                        total_encountered += encountered
                        total_duplicates += dups
                        total_pages = page_num
                        
                        logger.info(f"Page {page_num}: {len(reviews)} avis parsés, {saved_count} sauvegardés")
                        
                        # Passage à la page suivante en cliquant "Suivant" pour garder la session
                        has_next = await self._goto_next_page(page)
                        if not has_next and page_num < max_pages:
                            # Fallback: si le clic Next a échoué mais que la pagination n'est pas terminée,
                            # on tente un chargement direct par URL de la page suivante.
                            try:
                                logger.info("Fallback pagination: chargement direct de la page suivante par URL")
                                next_page = await self.fetcher.fetch_page(
                                    asin,
                                    page_num + 1,
                                    domain=domain,
                                    language=language,
                                    sort=sort,
                                    reviewer_type=reviewer_type,
                                )
                                if next_page:
                                    page = next_page
                                    has_next = True
                            except Exception as e:
                                logger.warning(f"Fallback direct page {page_num+1} échoué: {e}")
                        detail = {
                            "page": page_num,
                            "reviews_parsed": encountered,
                            "saved": saved_count,
                            "duplicates": dups,
                            "duration_s": round(time.time() - started_at, 2),
                            "next": has_next,
                            "error": None,
                        }
                        pages_details.append(detail)
                        if progress_cb:
                            try:
                                progress_cb(detail)
                            except Exception:
                                # Ne jamais interrompre le scraping pour un souci d'UI
                                pass
                        if not has_next:
                            logger.info("Pas de page suivante, arrêt de la pagination")
                            break
                        
                        # Pause entre les pages
                        await async_random_sleep()
                        
                        # On garde la même page (contexte persistant)
                        
                    except Exception as e:
                        error_msg = f"Erreur sur la page {page_num}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        detail_err = {
                            "page": page_num,
                            "reviews_parsed": 0,
                            "saved": 0,
                            "duplicates": 0,
                            "duration_s": round(time.time() - started_at, 2) if 'started_at' in locals() else None,
                            "next": False,
                            "error": str(e),
                        }
                        pages_details.append(detail_err)
                        if progress_cb:
                            try:
                                progress_cb(detail_err)
                            except Exception:
                                pass
                        continue
        
        except Exception as e:
            error_msg = f"Erreur générale lors du scraping de {asin}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Statistiques finales
        stats = {
            "asin": asin,
            "total_reviews": total_reviews,
            "total_encountered": total_encountered,
            "total_duplicates": total_duplicates,
            "total_pages": total_pages,
            "errors": errors,
            "success": len(errors) == 0,
            "pages_details": pages_details,
        }
        
        logger.info(f"Scraping terminé pour {asin}: {total_reviews} avis sur {total_pages} pages")
        
        return stats
    
    async def _goto_next_page(self, page) -> bool:
        """Clique sur le bouton "Suivant" s'il existe et attend le chargement."""
        try:
            # Amazon varie la structure: privilégier le lien explicite "Suivant" dans la pagination
            next_candidates = [
                'ul.a-pagination li.a-last a',
                'a[aria-label*="Suivant"]',
                'a[aria-label*="Next"]',
                'a[data-hook="pagination-bar-next"]',
                'ul.a-pagination a[href*="pageNumber="]',
            ]
            next_button = None
            for sel in next_candidates:
                el = await page.query_selector(sel)
                if el:
                    next_button = el
                    break
            if not next_button:
                return False

            await next_button.click()
            await page.wait_for_load_state("networkidle")
            try:
                await page.wait_for_selector('#cm_cr-review_list, [data-hook="review"]', timeout=10000)
            except Exception:
                pass
            return True
        except Exception as e:
            logger.warning(f"Erreur lors de la navigation vers la page suivante: {e}")
            return False
    
    async def _save_reviews(self, reviews: List[dict]) -> int:
        """
        Sauvegarde les avis en base de données.
        
        Args:
            reviews: Liste des avis à sauvegarder
            
        Returns:
            Nombre d'avis sauvegardés
        """
        if not reviews:
            return 0
        
        saved_count = 0
        
        # Utilisation d'une session de base de données
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            for review_data in reviews:
                try:
                    # Création de l'objet Review
                    asin_val = str(review_data.get("asin") or "").strip()
                    review_id_val = (review_data.get("review_id") or "").strip()
                    title_val = (review_data.get("review_title") or "").strip()
                    body_val = (review_data.get("review_body") or "").strip()
                    date_val = (review_data.get("review_date") or "").strip()

                    # Déduplication stricte: par review_id si présent
                    if review_id_val:
                        exists = (
                            db.query(Review.id)
                            .filter(Review.review_id == review_id_val)
                            .first()
                        )
                        if exists:
                            logger.debug(
                                f"Avis déjà existant (review_id match): {review_id_val}"
                            )
                            continue
                    # Sinon, déduplication par contenu (asin + titre + corps [+ date])
                    else:
                        q = (
                            db.query(Review.id)
                            .filter(Review.asin == asin_val)
                            .filter(Review.review_title == title_val)
                            .filter(Review.review_body == body_val)
                        )
                        if date_val:
                            q = q.filter(Review.review_date == date_val)
                        exists = q.first()
                        if exists:
                            logger.debug(
                                "Avis déjà existant (contenu équivalent, sans review_id)"
                            )
                            continue

                    review = Review(**review_data)
                    db.add(review)
                    db.commit()
                    saved_count += 1
                    
                except IntegrityError as e:
                    # Gestion des doublons (review_id unique)
                    db.rollback()
                    logger.debug(f"Avis déjà existant (ID: {review_data.get('review_id')}): {e}")
                    continue
                
                except Exception as e:
                    db.rollback()
                    logger.error(f"Erreur lors de la sauvegarde d'un avis: {e}")
                    continue
        
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de la sauvegarde des avis: {e}")
        
        finally:
            db.close()
        
        return saved_count
    
    async def scrape_batch(self, asins: List[str], concurrency: int = 1) -> List[dict]:
        """
        Scrape plusieurs ASINs en lot.
        
        Args:
            asins: Liste des ASINs à scraper
            concurrency: Niveau de concurrence (actuellement non utilisé)
            
        Returns:
            Liste des statistiques de scraping pour chaque ASIN
        """
        results = []
        
        logger.info(f"Début du scraping en lot de {len(asins)} ASINs")
        
        for i, asin in enumerate(asins, 1):
            logger.info(f"Traitement de l'ASIN {i}/{len(asins)}: {asin}")
            
            try:
                stats = await self.scrape_asin(asin)
                results.append(stats)
                
            except Exception as e:
                error_msg = f"Erreur lors du scraping de {asin}: {e}"
                logger.error(error_msg)
                results.append({
                    "asin": asin,
                    "total_reviews": 0,
                    "total_pages": 0,
                    "errors": [error_msg],
                    "success": False,
                })
        
        # Statistiques globales
        total_reviews = sum(r["total_reviews"] for r in results)
        successful_asins = sum(1 for r in results if r["success"])
        
        logger.info(f"Scraping en lot terminé: {total_reviews} avis au total, {successful_asins}/{len(asins)} ASINs réussis")
        
        return results
    
    def get_reviews_for_asin(self, asin: str, limit: Optional[int] = None) -> List[dict]:
        """
        Récupère les avis d'un ASIN depuis la base de données.
        
        Args:
            asin: ASIN du produit
            limit: Limite du nombre d'avis (optionnel)
            
        Returns:
            Liste des avis
        """
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            query = db.query(Review).filter(Review.asin == asin).order_by(Review.review_date.desc())
            
            if limit:
                query = query.limit(limit)
            
            reviews = query.all()
            return [review.to_dict() for review in reviews]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des avis pour {asin}: {e}")
            return []
        
        finally:
            db.close()
    
    def get_all_reviews(self, limit: Optional[int] = None) -> List[dict]:
        """
        Récupère tous les avis de la base de données.
        
        Args:
            limit: Limite du nombre d'avis (optionnel)
            
        Returns:
            Liste de tous les avis
        """
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            query = db.query(Review).order_by(Review.created_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            reviews = query.all()
            return [review.to_dict() for review in reviews]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de tous les avis: {e}")
            return []
        
        finally:
            db.close()

    def get_reviews_for_asin_since(self, asin: str, created_after: datetime, limit: Optional[int] = None) -> List[dict]:
        """
        Récupère les avis d'un ASIN insérés depuis un instant donné.
        """
        db_gen = get_db()
        db = next(db_gen)
        try:
            query = (
                db.query(Review)
                .filter(Review.asin == asin)
                .filter(Review.created_at >= created_after)
                .order_by(Review.created_at.desc())
            )
            if limit:
                query = query.limit(limit)
            reviews = query.all()
            return [review.to_dict() for review in reviews]
        except Exception as e:
            logger.error(f"Erreur get_reviews_for_asin_since pour {asin}: {e}")
            return []
        finally:
            db.close()

    def delete_reviews_for_asin(self, asin: str) -> int:
        """
        Supprime tous les avis d'un ASIN de la base.

        Returns:
            Nombre de lignes supprimées
        """
        db_gen = get_db()
        db = next(db_gen)
        try:
            deleted = db.query(Review).filter(Review.asin == asin).delete(synchronize_session=False)
            db.commit()
            logger.info(f"Suppression de {deleted} avis pour l'ASIN {asin}")
            return deleted
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de la suppression des avis pour {asin}: {e}")
            return 0
        finally:
            db.close()
