"""Mini interface Streamlit pour lancer le scraping, s'authentifier et exporter."""

import asyncio
import os
from pathlib import Path
import pandas as pd
import subprocess
import streamlit as st

from app.scrape import AmazonScraper
from app.utils import setup_logging, validate_asin, parse_amazon_url, detect_login_page
from app.config import settings
from app.fetch import AmazonFetcher


def run_async(coro):
    """Exécute une coroutine dans l'event loop de Streamlit."""
    return asyncio.run(coro)


st.set_page_config(page_title="Amazon Reviews Scraper", layout="wide")
st.title("🛒 Amazon Reviews Scraper")
st.caption("Utilisez avec modération et respect des CGU Amazon.")

setup_logging("INFO")

# Option: installation auto de Chromium sur Streamlit Cloud si absent
try:
    import shutil
    if shutil.which("playwright") and not shutil.which("chromium"):
        # Essayer une installation silencieuse (sera ignorée si déjà présent)
        subprocess.run(["python", "-m", "playwright", "install", "chromium", "--with-deps"], check=False)
except Exception:
    pass

tab1, tab2, tab3, tab4 = st.tabs(["Scraper", "Export", "Authentification", "Guide"]) 

with tab1:
    st.subheader("Scraper un ASIN")
    st.caption("Renseignez un ASIN ou une URL Amazon. Si l’URL contient l’ASIN, il sera détecté automatiquement.")
    asin = st.text_input(
        "ASIN",
        placeholder="B08N5WRWNW",
        help="Identifiant produit Amazon à 10 caractères alphanumériques (ex: B08N5WRWNW).",
    )
    url = st.text_input(
        "URL Amazon (produit ou avis)",
        placeholder="https://www.amazon.fr/.../dp/B0CJMJPXR1 ... ou ... /product-reviews/B0CJMJPXR1",
        help="Collez une URL de page produit ou directement de la page d’avis. L’ASIN et la langue seront déduits si possible.",
    )
    language_choice = st.selectbox(
        "Langue",
        options=["Auto (déduite)", "fr_FR", "en_US", "de_DE", "es_ES", "it_IT"],
        index=0,
        help="Forcer la langue des avis. Par défaut, déduite de l’URL.",
    )
    max_pages = st.number_input(
        "Nombre de pages max",
        min_value=1,
        max_value=100,
        value=2,
        help="Limite supérieure de pagination. Le scraping s’arrête si plus de pages ou s’il n’y a plus d’avis.",
    )
    reset_history = st.checkbox(
        "Réinitialiser l'historique pour cet ASIN",
        value=False,
        help="Supprime tous les avis existants pour cet ASIN avant le run.",
    )
    verbose = st.checkbox("Mode verbeux", value=False, help="Active des logs plus détaillés pendant le scraping.")
    start = st.button("Lancer le scraping", help="Démarrer le scraping selon les paramètres ci-dessus.")

    if start:
        if url:
            parsed = parse_amazon_url(url)
            if not parsed or not parsed.get("asin"):
                st.error("URL Amazon invalide. Fournissez une URL de produit ou d'avis Amazon valide.")
                st.stop()
            asin = parsed["asin"]
        if not validate_asin(asin):
            st.error("ASIN invalide. Il doit contenir exactement 10 caractères alphanumériques.")
        else:
            # Placeholders UX enrichis
            progress_bar = st.progress(0, text="Prêt à démarrer…")
            stats_cols = st.columns(4)
            page_ph = stats_cols[0].empty()
            parsed_ph = stats_cols[1].empty()
            saved_ph = stats_cols[2].empty()
            duration_ph = stats_cols[3].empty()
            eta_placeholder = st.empty()
            chart_placeholder = st.empty()
            live_table_placeholder = st.empty()
            live_rows = []

            with st.status("Scraping en cours…", expanded=False) as status:
                scraper = AmazonScraper()
                run_started_at = pd.Timestamp.utcnow()
                domain = parsed.get("domain") if url else None
                # Priorité à la langue choisie dans l'UI, sinon celle déduite de l'URL
                chosen_lang = None if language_choice.startswith("Auto") else language_choice
                language = chosen_lang or (parsed.get("language") if url else None)

                # Option: purge de l'historique existant pour cet ASIN
                if reset_history:
                    try:
                        deleted = scraper.delete_reviews_for_asin(asin)
                        st.info(f"Historique réinitialisé: {deleted} avis supprimés pour {asin}")
                    except Exception:
                        st.warning("Réinitialisation ignorée (erreur) — le scraping continue")

                # Callback de progression (appelé à chaque page)
                def _progress_cb(detail: dict):
                    try:
                        live_rows.append(detail)
                        df_live = pd.DataFrame(live_rows)
                        df_live = df_live[[c for c in ["page", "reviews_parsed", "saved", "duration_s", "next", "error"] if c in df_live.columns]]
                        live_table_placeholder.dataframe(df_live, use_container_width=True)
                        current_page = int(detail.get("page", 0) or 0)
                        pct = int(min(100, round((current_page / max(1, int(max_pages))) * 100)))
                        progress_bar.progress(pct, text=f"Page {current_page}/{int(max_pages)} • {pct}%")

                        # Cartes de métriques
                        page_ph.metric("Page", f"{current_page}/{int(max_pages)}")
                        parsed_ph.metric("Avis parsés (page)", int(detail.get("reviews_parsed", 0) or 0))
                        total_saved = int(df_live.get("saved", pd.Series(dtype=int)).fillna(0).sum()) if "saved" in df_live else 0
                        saved_ph.metric("Avis enregistrés (cumul)", total_saved)
                        duration_ph.metric("Durée page (s)", float(detail.get("duration_s", 0) or 0))

                        # ETA (estimation simple)
                        try:
                            if "duration_s" in df_live and not df_live["duration_s"].empty:
                                avg_dur = float(df_live["duration_s"].fillna(0).mean())
                                remaining = max(0, int(max_pages) - current_page)
                                eta_s = int(round(avg_dur * remaining))
                                if remaining > 0:
                                    eta_placeholder.caption(f"ETA ~ {eta_s}s restants (durée moyenne {avg_dur:.1f}s/page)")
                                else:
                                    eta_placeholder.caption("Presque terminé…")
                        except Exception:
                            pass

                        # Mini graphique (avis enregistrés par page)
                        try:
                            if "page" in df_live and "saved" in df_live:
                                df_plot = df_live[["page", "saved"]].set_index("page")
                                chart_placeholder.bar_chart(df_plot)
                        except Exception:
                            pass

                        # Mettre à jour le statut en cours
                        try:
                            status.update(label=f"Traitement page {current_page}…", state="running")
                        except Exception:
                            pass
                    except Exception:
                        pass

                stats = run_async(scraper.scrape_asin(
                    asin,
                    max_pages=int(max_pages),
                    domain=domain,
                    language=language,
                    progress_cb=_progress_cb,
                ))
            # Mettre à jour le statut final selon le résultat
            try:
                if stats.get("success"):
                    # Fermer proprement la barre en la remplissant à 100%
                    progress_bar.progress(100, text="Terminé • 100%")
                else:
                    progress_bar.progress(min(100, progress_bar._value or 0), text="Terminé avec erreurs")
            except Exception:
                pass
            # Affichage récapitulatif clair pour utilisateur novice
            st.markdown("### Résultat")
            status_msg_ok = (
                f"✅ Terminé: {stats.get('total_reviews',0)} avis sauvegardés sur {stats.get('total_pages',0)} pages"
                f" • {stats.get('total_encountered',0)} rencontrés"
                f" • {stats.get('total_duplicates',0)} doublons"
            )
            status_msg_warn = f"⚠ Terminé avec erreurs: {len(stats.get('errors', []))} erreurs"
            if stats.get("success"):
                st.success(status_msg_ok)
            else:
                st.warning(status_msg_warn)

            # Détails par page
            pages_details = stats.get("pages_details") or []
            if pages_details:
                df_pages = pd.DataFrame(pages_details)
                df_pages = df_pages[[c for c in ["page", "reviews_parsed", "saved", "duration_s", "next", "error"] if c in df_pages.columns]]
                st.markdown("#### Détail par page")
                st.dataframe(df_pages, use_container_width=True)

                # Indicateur pagination complète
                try:
                    last_next = bool(df_pages.iloc[-1]["next"]) if not df_pages.empty and "next" in df_pages.columns else None
                    total_pages = int(stats.get("total_pages") or len(df_pages))
                    asked_pages = int(max_pages)
                    is_complete = (total_pages == asked_pages) or (last_next is False)
                    st.caption(f"Pagination: {total_pages}/{asked_pages} pages • " + ("✅ complète" if is_complete else "⚠ incomplète"))
                except Exception:
                    pass

                # Export du détail de pagination
                csv_pages = df_pages.to_csv(index=False).encode("utf-8")
                st.download_button("Exporter le détail de pagination (CSV)", data=csv_pages, file_name=f"pages_details_{asin}.csv", mime="text/csv")

            # (section fusionnée ci-dessous)

            # Résultats & aperçu (fusion: derniers 10 + aperçu trié)
            try:
                # Priorité aux avis insérés pendant ce run
                try:
                    recent_inserted = scraper.get_reviews_for_asin_since(asin, created_after=run_started_at.to_pydatetime())
                except Exception:
                    recent_inserted = []
                if recent_inserted:
                    all_reviews = pd.DataFrame(recent_inserted)
                else:
                    all_reviews = pd.DataFrame(scraper.get_reviews_for_asin(asin))
                if not all_reviews.empty:
                    # Déduplication de secours côté UI pour garantir zéro doublon visible
                    dedupe_cols = [c for c in ["asin", "review_title", "review_body", "review_date"] if c in all_reviews.columns]
                    if dedupe_cols:
                        all_reviews = all_reviews.drop_duplicates(subset=dedupe_cols, keep="first")
                    def _sentiment_from_rating(r: float) -> str:
                        try:
                            val = float(r)
                        except Exception:
                            return "Neutre"
                        if val >= 4:
                            return "Positif"
                        if val <= 2:
                            return "Négatif"
                        return "Neutre"
                    st.markdown("#### Résultats et aperçu")
                    tab_last, tab_preview = st.tabs(["Chronologique", "Aperçu trié par sentiment"])

                    # Vue 1: Derniers 10 avis (par date de création si dispo, sinon review_date)
                    with tab_last:
                        sort_cols = [c for c in ["created_at", "review_date"] if c in all_reviews.columns]
                        df_last = all_reviews.copy()
                        if sort_cols:
                            df_last = df_last.sort_values(sort_cols, ascending=[False] * len(sort_cols))
                        cols_last = [c for c in ["review_id", "review_date", "rating", "review_title", "review_body", "reviewer_name", "variant"] if c in df_last.columns]
                        st.dataframe(df_last[cols_last], use_container_width=True)
                        # Exports de la vue chronologique complète
                        c1, c2 = st.columns(2)
                        with c1:
                            st.download_button(
                                "CSV (chronologique)",
                                data=df_last.to_csv(index=False).encode("utf-8"),
                                file_name=f"reviews_chrono_{asin}.csv",
                                mime="text/csv",
                                key=f"dl_chrono_csv_{asin}",
                            )
                        with c2:
                            try:
                                import io
                                out = io.BytesIO()
                                with pd.ExcelWriter(out, engine="openpyxl") as writer:
                                    df_last.to_excel(writer, index=False, sheet_name="chronologique")
                                st.download_button(
                                    "Excel (chronologique)",
                                    data=out.getvalue(),
                                    file_name=f"reviews_chrono_{asin}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key=f"dl_chrono_xlsx_{asin}",
                                )
                            except Exception:
                                pass

                    # Vue 2: Aperçu trié par sentiment
                    with tab_preview:
                        all_reviews["sentiment"] = all_reviews.get("rating", 0).apply(_sentiment_from_rating)
                        order = ["Positif", "Neutre", "Négatif"]
                        all_reviews["sentiment"] = pd.Categorical(all_reviews["sentiment"], categories=order, ordered=True)
                        df_preview = all_reviews.sort_values(["sentiment", "review_date"], ascending=[True, False])
                        st.dataframe(df_preview, use_container_width=True)

                        col1, col2 = st.columns(2)
                        with col1:
                            csv_bytes = df_preview.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                "CSV (aperçu trié)",
                                data=csv_bytes,
                                file_name=f"reviews_{asin}.csv",
                                mime="text/csv",
                                key=f"dl_csv_sorted_{asin}",
                            )
                        with col2:
                            try:
                                import io
                                output = io.BytesIO()
                                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                                    df_preview.to_excel(writer, index=False, sheet_name="reviews")
                                st.download_button(
                                    "Excel (aperçu trié)",
                                    data=output.getvalue(),
                                    file_name=f"reviews_{asin}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key=f"dl_xlsx_sorted_{asin}",
                                )
                            except Exception:
                                pass
            except Exception:
                pass

            # Afficher erreurs si présentes
            if stats.get("errors"):
                with st.expander("Voir les erreurs"):
                    for err in stats["errors"]:
                        st.write(f"- {err}")

with tab2:
    st.subheader("Exporter les avis")
    st.caption("Téléchargez les avis déjà stockés en base. Laissez l’ASIN vide pour exporter tout le jeu de données.")
    # Conserver l'état entre les reruns pour éviter la disparition des boutons après clic
    if "export_df" not in st.session_state:
        st.session_state["export_df"] = None
    asin_filter = st.text_input(
        "Filtrer par ASIN (optionnel)",
        help="Exporter uniquement les avis correspondant à cet ASIN. Laissez vide pour tout exporter.",
    )
    limit = st.number_input(
        "Limiter le nombre d'avis (optionnel)",
        min_value=0,
        max_value=10000,
        value=0,
        help="0 pour aucune limite. Utile pour échantillonner les données.",
    )
    do_export = st.button("Préparer l'export", help="Préparer les fichiers téléchargeables ci-dessous.")

    if do_export:
        scraper = AmazonScraper()
        lim = int(limit) if limit > 0 else None
        data = scraper.get_reviews_for_asin(asin_filter, lim) if asin_filter else scraper.get_all_reviews(lim)
        if not data:
            st.session_state["export_df"] = None
            st.info("Aucun avis en base.")
        else:
            st.session_state["export_df"] = pd.DataFrame(data)

    # Proposer les deux formats d'export tant que des données sont prêtes
    if st.session_state.get("export_df") is not None:
        df = st.session_state["export_df"]
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button(
                "Télécharger CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="reviews.csv",
                mime="text/csv",
                key="dl_csv_global",
            )
        with col_b:
            try:
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="reviews")
                st.download_button(
                    "Télécharger Excel",
                    data=output.getvalue(),
                    file_name="reviews.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_xlsx_global",
                )
            except Exception:
                st.warning("Excel indisponible: vérifiez l'installation d'openpyxl.")

with tab3:
    st.subheader("Authentification Amazon")
    st.caption("Ouvrez une fenêtre pour vous connecter, la session sera enregistrée.")
    with st.expander("Comment ça marche ?"):
        st.markdown(
            "- Une fenêtre Amazon s’ouvre avec Playwright.\n"
            "- Connectez-vous normalement (email, mot de passe, 2FA si nécessaire).\n"
            "- À la détection de session valide, l’état est sauvegardé pour les prochains scrapings."
        )

    session_state_path = getattr(settings, "storage_state_path", "./storage_state.json")
    if os.path.exists(session_state_path):
        st.success(f"Session trouvée: {session_state_path}")
    else:
        st.info("Aucune session enregistrée.")

    if st.button("Ouvrir la fenêtre de connexion Amazon", help="Lancer une fenêtre contrôlée pour se connecter à Amazon."):
        with st.spinner("Ouverture de la fenêtre de connexion..."):
            old = settings.headless
            settings.headless = False
            async def run_login(timeout_sec: int = 600) -> bool:
                fetcher = AmazonFetcher()
                await fetcher.start_browser()
                context = await fetcher.create_context()
                page = await context.new_page()
                # Accueil FR puis navigation via header
                await page.goto("https://www.amazon.fr/", wait_until="domcontentloaded", timeout=settings.timeout_ms)
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
                try:
                    acc = await page.wait_for_selector('#nav-link-accountList', timeout=8000)
                    await acc.click()
                    await page.wait_for_load_state("domcontentloaded")
                except Exception:
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
                import time as _t
                start = _t.time()
                logged = False
                while _t.time() - start < timeout_sec:
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
                if logged:
                    await context.storage_state(path=session_state_path)
                await fetcher.stop_browser()
                return logged
            ok = asyncio.run(run_login())
            settings.headless = old
            if ok:
                st.success(f"✓ Session enregistrée: {session_state_path}")
            else:
                st.error("Connexion non détectée dans le délai imparti.")

with tab4:
    st.subheader("Guide d’utilisation")
    st.markdown("""
### 1) Scraper un produit
- Renseignez un **ASIN** ou collez une **URL Amazon** (produit ou avis). Si l’URL contient l’ASIN, il sera détecté.
- Choisissez la **langue** (ou laissez en Auto). Réglez le **nombre de pages max**.
- Cliquez sur **Lancer le scraping**. Suivez la **progression** et le **détail par page**.

### 2) Exporter les avis
- Allez dans l’onglet **Export**. Filtrez par **ASIN** si besoin, sinon laissez vide.
- Choisissez le **format** (CSV ou Parquet) puis cliquez sur **Exporter**.

### 3) Authentification Amazon
- Ouvrez une fenêtre de connexion depuis l’onglet **Authentification**.
- Connectez-vous; la **session** est enregistrée pour les scrapings suivants.

### Conseils et bonnes pratiques
- Respectez les **CGU Amazon** et limitez la fréquence (pauses min/max dans la barre latérale).
- Pour une meilleure stabilité, commencez avec **peu de pages** puis augmentez.
- Surveillez la section **erreurs** en fin de scraping. Relancez si besoin.

### Dépannage
- Si aucune donnée n’apparaît: vérifiez l’ASIN/URL et la **langue**.
- Si Amazon demande un captcha/2FA: passez par l’onglet **Authentification** puis réessayez.
- Erreurs réseau sporadiques: **relancez** le scraping, réduisez **pages max**, augmentez les **pauses**.
    """)

st.sidebar.header("Configuration rapide")
st.sidebar.caption("Paramètres appliqués au processus courant. Utiles pour ajuster le rythme et la stabilité.")
headless = st.sidebar.checkbox("Headless (recommandé)", value=True, help="Exécute le navigateur sans interface graphique pour plus de performances.")
pages_env = st.sidebar.number_input("Pages max par défaut", min_value=1, max_value=100, value=5, help="Valeur utilisée si vous ne précisez pas de limite dans l’onglet Scraper.")
sleep_min = st.sidebar.number_input("Pause min (s)", min_value=0.0, value=2.0, help="Délai minimum aléatoire entre les pages.")
sleep_max = st.sidebar.number_input("Pause max (s)", min_value=0.0, value=4.0, help="Délai maximum aléatoire entre les pages.")

if st.sidebar.button("Appliquer", help="Enregistrer ces paramètres dans les variables d’environnement du processus courant."):
    # Applique à l'environnement courant du process (simple)
    os.environ["HEADLESS"] = "true" if headless else "false"
    os.environ["MAX_PAGES_PER_ASIN"] = str(int(pages_env))
    os.environ["SLEEP_MIN"] = str(float(sleep_min))
    os.environ["SLEEP_MAX"] = str(float(sleep_max))
    st.sidebar.success("Configuration appliquée (process courant)")

st.sidebar.markdown("---")
st.sidebar.write("Pour lancer:")
st.sidebar.code("streamlit run streamlit_app.py")


