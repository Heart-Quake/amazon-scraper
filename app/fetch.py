"""Module de récupération des pages avec gestion des proxies et anti-bot."""

import logging
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.utils import (
    ProxyPool,
    UserAgentPool,
    async_random_sleep,
    detect_anti_bot,
    detect_error_page,
    detect_login_page,
    generate_review_url,
    generate_product_url,
    validate_asin,
)

logger = logging.getLogger(__name__)


class AmazonFetcher:
    """Gestionnaire de récupération des pages Amazon avec anti-bot."""
    
    def __init__(self):
        """Initialise le fetcher avec les pools de proxies et User-Agents."""
        self.proxy_pool = ProxyPool(settings.proxy_pool)
        self.ua_pool = UserAgentPool()
        self.browser: Optional[Browser] = None
        self.playwright: Optional[Playwright] = None
        # Indique si self.browser est un BrowserContext persistant
        self._is_persistent_context: bool = False
    
    async def start_browser(self) -> None:
        """Démarre le navigateur Playwright."""
        try:
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            
            # Configuration du navigateur
            browser_args = [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
            ]
            
            if settings.use_persistent_profile:
                import os
                os.makedirs(settings.user_data_dir, exist_ok=True)
                try:
                    # Mode profil persistant (plus robuste pour conserver la session)
                    self.browser = await self.playwright.chromium.launch_persistent_context(
                        settings.user_data_dir,
                        headless=settings.headless,
                        args=browser_args,
                        locale="fr-FR",
                        timezone_id="Europe/Paris",
                        viewport={"width": 1280, "height": 900},
                    )
                    self._is_persistent_context = True
                except Exception as e:
                    # Fallback automatique: profils verrouillés/corrompus ou instance existante
                    logger.warning(
                        f"Échec du lancement persistant ({e}). Bascule en mode non persistant avec storage_state si disponible."
                    )
                    self.browser = await self.playwright.chromium.launch(
                        headless=settings.headless,
                        args=browser_args,
                    )
                    self._is_persistent_context = False
            else:
                # Mode non persistant standard
                self.browser = await self.playwright.chromium.launch(
                    headless=settings.headless,
                    args=browser_args,
                )
                self._is_persistent_context = False
            
            logger.info("Navigateur démarré avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du navigateur: {e}")
            raise
    
    async def stop_browser(self) -> None:
        """Arrête le navigateur Playwright."""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            logger.info("Navigateur arrêté")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du navigateur: {e}")
    
    async def create_context(self, proxy: Optional[str] = None) -> BrowserContext:
        """
        Crée un contexte de navigateur avec proxy et User-Agent.
        
        Args:
            proxy: Proxy à utiliser (optionnel)
            
        Returns:
            Contexte de navigateur configuré
        """
        if not self.browser:
            raise RuntimeError("Le navigateur n'est pas démarré")
        
        # Si on est en mode profil persistant, self.browser est déjà un context
        if self._is_persistent_context:
            context = self.browser  # type: ignore
        else:
            # Configuration du contexte normal
            context_options = {
                "user_agent": self.ua_pool.get_random_ua(),
                "locale": "fr-FR",
                "timezone_id": "Europe/Paris",
                "viewport": {"width": 1920, "height": 1080},
            }
            if proxy:
                context_options["proxy"] = {"server": proxy}
                logger.debug(f"Utilisation du proxy: {proxy}")
            storage_state = None
            try:
                import os
                if os.path.exists(settings.storage_state_path):
                    storage_state = settings.storage_state_path
            except Exception:
                storage_state = None
            if storage_state:
                context = await self.browser.new_context(storage_state=storage_state, **context_options)  # type: ignore
            else:
                context = await self.browser.new_context(**context_options)  # type: ignore

        # Bloquer certaines ressources pour accélérer et limiter détection (pattern Octoparse-like)
        try:
            await context.route("**/*", lambda route: route.continue_())
            block_ext = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".woff", ".woff2", ".ttf")
            async def route_handler(route):
                req = route.request
                url = req.url.lower()
                if any(url.endswith(ext) for ext in block_ext):
                    return await route.abort()
                return await route.continue_()
            await context.unroute("**/*")
            await context.route("**/*", route_handler)
        except Exception:
            pass
        
        # Ajout d'headers supplémentaires pour éviter la détection
        await context.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            # Client hints basiques
            "sec-ch-ua": '"Chromium";v="126", "Not=A?Brand";v="24"',
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "navigate",
            "sec-fetch-user": "?1",
            "sec-fetch-dest": "document",
        })
        
        # Scripts d'évasion simples (navigator.webdriver, languages)
        try:
            await context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});
                Object.defineProperty(navigator, 'language', {get: () => 'fr-FR'});
                Object.defineProperty(navigator, 'languages', {get: () => ['fr-FR','fr','en']});
                """
            )
        except Exception:
            pass

        # Cookies régionaux FR pour réduire les redirections
        try:
            await context.add_cookies([
                {"name": "lc-main", "value": "fr_FR", "domain": ".amazon.fr", "path": "/"},
                {"name": "i18n-prefs", "value": "EUR", "domain": ".amazon.fr", "path": "/"},
            ])
        except Exception:
            pass
        
        return context

    async def ensure_logged_in(self, context: BrowserContext) -> None:
        """Tente de se connecter si credentials fournis et pas de storage_state."""
        try:
            if not settings.amz_email or not settings.amz_password:
                return
            page = await context.new_page()
            await page.goto("https://www.amazon.fr/ap/signin", wait_until="domcontentloaded", timeout=settings.timeout_ms)
            # Remplir formulaire
            email_sel = 'input#ap_email'
            cont_btn = 'input#continue'
            pass_sel = 'input#ap_password'
            sign_btn = 'input#signInSubmit'
            if await page.query_selector(email_sel):
                await page.fill(email_sel, settings.amz_email)
                btn = await page.query_selector(cont_btn)
                if btn:
                    await btn.click()
                    await page.wait_for_load_state("domcontentloaded")
            if await page.query_selector(pass_sel):
                await page.fill(pass_sel, settings.amz_password)
                btn2 = await page.query_selector(sign_btn)
                if btn2:
                    await btn2.click()
                    await page.wait_for_load_state("networkidle")
            # Sauvegarder l'état si on a un indicateur d'être connecté (présence de nav account)
            try:
                nav_acc = await page.query_selector('#nav-link-accountList')
                if nav_acc:
                    await context.storage_state(path=settings.storage_state_path)
            except Exception:
                pass
            await page.close()
        except Exception as e:
            logger.warning(f"Connexion Amazon échouée/ignorée: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=10),
        reraise=True,
    )
    async def fetch_page(
        self,
        asin: str,
        page_number: int = 1,
        proxy: Optional[str] = None,
        *,
        domain: Optional[str] = None,
        language: Optional[str] = None,
        sort: Optional[str] = None,
        reviewer_type: Optional[str] = None,
    ) -> Page:
        """
        Récupère une page d'avis avec gestion des erreurs et retry.
        
        Args:
            asin: ASIN du produit
            page_number: Numéro de page
            proxy: Proxy à utiliser (optionnel)
            
        Returns:
            Page Playwright chargée
            
        Raises:
            ValueError: Si l'ASIN est invalide
            RuntimeError: Si la page contient des éléments anti-bot
        """
        if not validate_asin(asin):
            raise ValueError(f"ASIN invalide: {asin}")
        
        if not self.browser:
            await self.start_browser()
        
        # Création du contexte
        context = await self.create_context(proxy)
        # Si storage state absent, tenter login si credentials fournis
        if not settings.use_persistent_profile:
            await self.ensure_logged_in(context)
        page = await context.new_page()
        
        try:
            # Warm-up: ouvrir d'abord la page produit pour initialiser cookies/région
            try:
                product_url = generate_product_url(asin, domain=domain)
                await page.goto(product_url, wait_until="domcontentloaded", timeout=settings.timeout_ms)
                # cliquer "Voir tous les avis" si présent
                view_all_sel = 'a[data-hook="see-all-reviews-link-foot"], a[href*="/product-reviews/"]'
                link = await page.query_selector(view_all_sel)
                if link:
                    await link.click()
                    await page.wait_for_load_state("networkidle")
                else:
                    # Alternative: accéder au menu d'avis via bloc d'étoiles
                    try:
                        stars = await page.query_selector('a[href*="/product-reviews/"]')
                        if stars:
                            await stars.click()
                            await page.wait_for_load_state("networkidle")
                    except Exception:
                        pass
            except Exception:
                pass

            # Génération de l'URL de la page d'avis cible
            url = generate_review_url(
                asin,
                page_number,
                language=language,
                sort=sort,
                domain=domain,
                reviewer_type=reviewer_type or "all_reviews",
            )
            logger.info(f"Récupération de la page {page_number} pour ASIN {asin}")
            logger.debug(f"URL: {url}")
            
            # Navigation vers la page d'avis (avec Referer produit)
            await page.set_extra_http_headers({"Referer": product_url})
            response = await page.goto(
                url,
                wait_until="networkidle",
                timeout=settings.timeout_ms,
            )

            # Attendre le conteneur liste avis si possible
            try:
                await page.wait_for_selector('#cm_cr-review_list, [data-hook="review"]', timeout=8000)
            except Exception:
                pass

            # Essayer de cliquer sur le bandeau cookies si présent
            try:
                # Amazon FR: bouton cookies commun
                cookie_selectors = [
                    'input#sp-cc-accept',
                    'input[name="accept"]',
                    'button[name="accept"]',
                    'input[data-cel-widget="sp-cc-accept"]',
                    'span.a-button-inner > input.a-button-input[type="submit"][aria-labelledby="a-autoid-0-announce"]',
                ]
                for sel in cookie_selectors:
                    btn = await page.query_selector(sel)
                    if btn:
                        await btn.click()
                        break
            except Exception:
                pass
            
            # Continuer même si status non-200 pour vérifier le contenu (Amazon renvoie parfois 200/HTML custom)
            if not response:
                raise RuntimeError("Aucune réponse")
            
            # Récupération du contenu pour vérification
            content = await page.content()
            
            # Vérification anti-bot
            if detect_anti_bot(content):
                logger.warning("Détection d'éléments anti-bot, retry avec nouveau proxy/UA")
                raise RuntimeError("Éléments anti-bot détectés")
            
            # Vérification d'erreur/login (plus permissive)
            if detect_login_page(content):
                logger.warning("Page de connexion détectée - besoin d'ajuster UA/proxy/langue")
            elif detect_error_page(content):
                logger.warning("Page potentiellement d'erreur détectée")
            
            # Pause aléatoire pour éviter la détection
            await async_random_sleep()
            
            logger.info(f"Page {page_number} récupérée avec succès")
            return page
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la page: {e}")
            await page.close()
            await context.close()
            raise
    
    async def fetch_reviews_page(
        self,
        asin: str,
        page_number: int = 1,
        *,
        domain: Optional[str] = None,
        language: Optional[str] = None,
        sort: Optional[str] = None,
        reviewer_type: Optional[str] = None,
    ) -> Optional[Page]:
        """
        Récupère une page d'avis avec rotation de proxy et gestion d'erreurs.
        
        Args:
            asin: ASIN du produit
            page_number: Numéro de page
            
        Returns:
            Page Playwright ou None en cas d'échec
        """
        max_attempts = 3
        proxies_to_try = []
        
        # Préparation de la liste des proxies à essayer
        if self.proxy_pool.has_proxies():
            proxies_to_try = [self.proxy_pool.get_next_proxy() for _ in range(max_attempts)]
        else:
            proxies_to_try = [None] * max_attempts
        
        for attempt in range(max_attempts):
            proxy = proxies_to_try[attempt] if attempt < len(proxies_to_try) else None
            
            try:
                logger.info(f"Tentative {attempt + 1}/{max_attempts} pour ASIN {asin}, page {page_number}")
                if proxy:
                    logger.debug(f"Utilisation du proxy: {proxy}")
                
                page = await self.fetch_page(
                    asin,
                    page_number,
                    proxy,
                    domain=domain,
                    language=language,
                    sort=sort,
                    reviewer_type=reviewer_type,
                )
                return page
                
            except Exception as e:
                logger.warning(f"Tentative {attempt + 1} échouée: {e}")

                # Fallback: au prochain essai, passer en UA mobile si bloqué
                if attempt == 0:
                    try:
                        logger.info("Activation du fallback User-Agent mobile pour le prochain essai")
                        self.ua_pool.user_agents = self.ua_pool.mobile_user_agents
                    except Exception:
                        pass
                
                if attempt < max_attempts - 1:
                    # Pause progressive entre les tentatives
                    wait_time = 2 ** attempt
                    logger.info(f"Attente de {wait_time} secondes avant la prochaine tentative")
                    await async_random_sleep(wait_time, wait_time + 1)
                else:
                    logger.error(f"Toutes les tentatives ont échoué pour ASIN {asin}, page {page_number}")
        
        return None
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.start_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop_browser()
