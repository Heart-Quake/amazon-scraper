"""Mini interface Streamlit pour lancer le scraping, s'authentifier et exporter."""

import asyncio
import os
from pathlib import Path
import uuid
import pandas as pd
import streamlit as st

from automation_seo_theme import apply_automation_seo_theme
from app.scrape import AmazonScraper
from app.utils import (
    setup_logging,
    validate_asin,
    parse_amazon_url,
    detect_login_page,
    generate_product_url,
)
from app.config import settings
from app.fetch import AmazonFetcher
from app.normalize import clean_text


def run_async(coro):
    """Exécute une coroutine dans l'event loop de Streamlit."""
    return asyncio.run(coro)


st.set_page_config(page_title="Amazon Reviews Scraper", layout="wide")
apply_automation_seo_theme()
st.markdown(
    """
    <section class="tool-hero">
        <div class="tool-kicker">Review scraping</div>
        <h1 class="tool-title">Amazon Reviews Scraper</h1>
        <p class="tool-lead">Collecte les avis Amazon, controle la qualite des donnees et prepare des exports propres pour analyse.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

setup_logging("INFO")

tab1, tab2, tab3, tab4 = st.tabs(["Scraper", "Export", "Authentification", "Qualité"]) 

# État persistant du dernier run (persiste à travers les reruns Streamlit)
if "last_run" not in st.session_state:
    st.session_state["last_run"] = {
        "id": None,
        "stats": None,
        "reviews_df": None,
        "pages_df": None,
    }

with tab1:
    st.subheader("Scraper un ASIN")
    asin = st.text_input("ASIN", placeholder="B08N5WRWNW")
    url = st.text_input("URL Amazon (produit ou avis)", placeholder="https://www.amazon.fr/.../dp/B0CJMJPXR1 ... ou ... /product-reviews/B0CJMJPXR1")
    col_site, col_adv = st.columns([1,1])
    with col_site:
        domain_choice = st.selectbox(
            "Site Amazon",
            options=[
                "Auto (déduit)",
                "www.amazon.fr",
                "www.amazon.es",
                "www.amazon.it",
                "www.amazon.nl",
                "www.amazon.de",
                "www.amazon.co.uk",
            ],
            index=0,
            help="Sélectionnez le domaine Amazon local (ou Auto).",
        )
    with col_adv:
        advanced_lang_override = st.checkbox("Forcer la langue (avancé)", value=False, key="scraper_lang_override")
    override_language = None
    if advanced_lang_override:
        override_language = st.selectbox(
            "Langue",
            options=["fr_FR", "en_GB", "de_DE", "es_ES", "it_IT", "nl_NL"],
            index=0,
            help="Forcer la langue. Sinon, elle est déduite du domaine.",
        )

    def _derive_language_from_domain(d: str) -> str:
        d = (d or "www.amazon.fr").lower()
        if d.endswith(".fr"): return "fr_FR"
        if d.endswith(".es"): return "es_ES"
        if d.endswith(".it"): return "it_IT"
        if d.endswith(".nl"): return "nl_NL"
        if d.endswith(".de"): return "de_DE"
        if d.endswith(".co.uk"): return "en_GB"
        return "fr_FR"
    colp1, colp2 = st.columns([2,1])
    with colp1:
        max_pages = st.number_input("Nombre de pages max", min_value=1, max_value=10000, value=2)
    with colp2:
        full_pagination = st.checkbox("Pagination complète", value=False, help="Ignorer la limite et paginer jusqu'à disparition du bouton 'Suivant'.")
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        verbose = st.checkbox("Mode verbeux", value=False)
    with col_cfg2:
        persist = st.checkbox("Sauvegarder en base", value=False, help="Si décoché, le run est éphémère: données en mémoire, exportables puis jetées.")

    star_map = {
        "Toutes": None,
        "5 étoiles": "five_star",
        "4 étoiles": "four_star",
        "3 étoiles": "three_star",
        "2 étoiles": "two_star",
        "1 étoile": "one_star",
    }
    star_choice = st.selectbox("Filtre étoiles", list(star_map.keys()), index=0, help="Scraper par tranche de notation (Amazon limite ~10 pages/100 avis par tranche)")
    multi_tranches = st.checkbox("Enchaîner toutes les tranches (5→1 étoiles)", value=False, help="Lance automatiquement 5,4,3,2,1 étoiles avec pagination complète si activée.")
    st.markdown("#### Batch d'URLs (optionnel)")
    urls_text = st.text_area("Collez des URLs Amazon (une par ligne)", height=120, placeholder="https://www.amazon.fr/...\nhttps://www.amazon.es/...\n")
    # Aperçu immédiat du nombre d'URLs détectées (valides)
    preview_urls = []
    if urls_text.strip():
        for line in urls_text.splitlines():
            line = line.strip()
            if not line:
                continue
            p = parse_amazon_url(line)
            if p and p.get("asin"):
                preview_urls.append(p)
    st.caption(f"URLs détectées: {len(preview_urls)}")
    colA, colB = st.columns([1,1])
    with colA:
        start = st.button("Lancer le scraping")
    with colB:
        check_auth = st.button("Vérifier la session Amazon")

    if check_auth:
        with st.spinner("Vérification de la session..."):
            ok = run_async(AmazonFetcher().check_session_valid())
            if ok:
                st.success("Session Amazon valide (storage_state.json chargé)")
            else:
                st.warning("Session invalide: ouvrez l’onglet Auth et reconnectez-vous")

    if start:
        # Initialiser un identifiant de run pour ce scraping
        st.session_state["last_run"]["id"] = uuid.uuid4().hex
        st.session_state["last_run"]["stats"] = None
        st.session_state["last_run"]["reviews_df"] = None
        st.session_state["last_run"]["pages_df"] = None
        batch_mode = bool(urls_text.strip())
        if url and not batch_mode:
            parsed = parse_amazon_url(url)
            if not parsed or not parsed.get("asin"):
                st.error("URL Amazon invalide. Fournissez une URL de produit ou d'avis Amazon valide.")
                st.stop()
            asin = parsed["asin"]
        # En mode batch, on ne force pas un ASIN unique dans le champ
        if not batch_mode and not validate_asin(asin):
            st.error("ASIN invalide. Il doit contenir exactement 10 caractères alphanumériques.")
        else:
            # Placeholders UX
            progress_bar = st.progress(0)
            live_table_placeholder = st.empty()
            live_rows = []

                # Déterminer d'abord le domaine et la langue cibles pour le pré-check
            # Domaine: choix explicite sinon domaine de l'URL (si non-batch), sinon défaut FR
            target_domain = None
            if domain_choice and not domain_choice.startswith("Auto"):
                target_domain = domain_choice
            elif url and not batch_mode and 'parsed' in locals() and parsed:
                target_domain = parsed.get("domain")
            else:
                target_domain = "www.amazon.fr"
            # Langue: override avancé sinon dérivée du domaine (optimisé, pas d'option visible par défaut)
            if advanced_lang_override and override_language:
                language = override_language
            else:
                language = _derive_language_from_domain(target_domain)
            # Pré-check d'auth rapide: spécifique au domaine/langue ciblés
            fetcher = AmazonFetcher()
            auth_ok = run_async(fetcher.check_session_valid_for(target_domain, language))
            if not auth_ok:
                st.warning(f"Session invalide pour {target_domain} / {language or 'auto'}. Ouvrez l’onglet Auth et reconnectez-vous sur ce domaine, puis relancez.")
                st.stop()
            # Réinitialiser les compteurs de progression
            st.session_state["_cum_saved_reviews"] = 0
            st.session_state["_total_header_reviews"] = None

            with st.spinner("Scraping en cours..."):
                scraper = AmazonScraper()
                # Domaine/langue pour le run: réutiliser ceux calculés au pré-check
                domain = target_domain
                # 'language' est déjà défini ci-dessus

                # Callback de progression (appelé à chaque page)
                def _progress_cb(detail: dict):
                    try:
                        live_rows.append(detail)
                        df_live = pd.DataFrame(live_rows)
                        # Ajouter ASIN + libellé tranche étoiles
                        if "asin" not in df_live.columns:
                            df_live["asin"] = asin
                        star_map_labels = {
                            "five_star": "5 étoiles",
                            "four_star": "4 étoiles",
                            "three_star": "3 étoiles",
                            "two_star": "2 étoiles",
                            "one_star": "1 étoile",
                            None: "Toutes",
                        }
                        if "star_filter" in df_live.columns:
                            df_live["star_label"] = df_live["star_filter"].map(star_map_labels).fillna("Toutes")
                        else:
                            df_live["star_label"] = "Toutes"
                # Colonnes affichées dans le tableau live
                        # Ajouter domaine et URL produit canonique si possible
                        if "asin" in df_live.columns:
                            try:
                                # Construire une colonne domain si absente
                                if "domain" not in df_live.columns:
                                    df_live["domain"] = (domain or "").strip() or (parsed.get("domain") if 'parsed' in locals() and parsed else "") or "www.amazon.fr"
                                df_live["canonical_product_url"] = df_live.apply(lambda r: generate_product_url(str(r.get("asin")), domain=str(r.get("domain") or "www.amazon.fr")), axis=1)
                            except Exception:
                                pass
                        cols_live = [c for c in ["asin", "domain", "canonical_product_url", "star_label", "page", "reviews_parsed", "saved", "duration_s", "next", "error"] if c in df_live.columns]
                        df_live = df_live[cols_live]
                        live_table_placeholder.dataframe(df_live, use_container_width=True)
                        # Sauvegarder un snapshot des pages pour persistance
                        st.session_state["last_run"]["pages_df"] = df_live.copy()
                        # Mettre à jour la progression: priorité au total entête si disponible
                        if detail.get("saved") is not None:
                            st.session_state["_cum_saved_reviews"] += int(detail.get("saved", 0))
                        if detail.get("total_reviews_header"):
                            st.session_state["_total_header_reviews"] = int(detail.get("total_reviews_header") or 0)
                        total_hdr = st.session_state.get("_total_header_reviews")
                        if total_hdr and total_hdr > 0:
                            pct = int(min(100, round((st.session_state["_cum_saved_reviews"] / total_hdr) * 100)))
                        else:
                            pct = int(min(100, round((detail.get("page", 0) / max(1, int(max_pages))) * 100)))
                        progress_bar.progress(max(0, min(100, pct)))
                    except Exception:
                        pass

                def _run_one(star):
                    use_full = bool(full_pagination) or bool(multi_tranches)
                    return run_async(scraper.scrape_asin(
                        asin,
                        max_pages=int(max_pages),
                        domain=domain,
                        language=language,
                        progress_cb=_progress_cb,
                        persist=bool(persist),
                        full_pagination=use_full,
                        star_filter=star,
                    ))

                url_list = []
                if urls_text.strip():
                    for line in urls_text.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        p = parse_amazon_url(line)
                        if p and p.get("asin"):
                            url_list.append(p)

                # Exécution batch si url_list sinon single
                if url_list:
                    # Placeholders progression lot (X/Y)
                    batch_total = len(url_list)
                    batch_done = 0
                    batch_info_placeholder = st.empty()
                    batch_bar = st.progress(0)
                    batch_info_placeholder.text(f"Progression lot: {batch_done}/{batch_total}")

                    all_stats = []
                    for p in url_list:
                        asin = p["asin"]
                        domain = domain or p.get("domain")
                        language = p.get("language") or language
                        if multi_tranches:
                            sequence = ["five_star","four_star","three_star","two_star","one_star"]
                            for sf in sequence:
                                st.info(f"ASIN {asin} – Tranche: {sf.replace('_',' ').title()}")
                                s = _run_one(sf)
                                all_stats.append(s)
                        else:
                            s = _run_one(star_map.get(star_choice))
                            all_stats.append(s)
                        # Mise à jour progression lot
                        batch_done += 1
                        pct = int(min(100, round((batch_done / batch_total) * 100))) if batch_total else 100
                        batch_info_placeholder.text(f"Progression lot: {batch_done}/{batch_total}")
                        batch_bar.progress(pct)
                    # Fusion des résultats batch
                    total_reviews_sum = sum([s.get("total_reviews", 0) for s in all_stats])
                    total_pages_sum = sum([s.get("total_pages", 0) for s in all_stats])
                    errors_agg = []
                    for s in all_stats:
                        errors_agg.extend(s.get("errors") or [])
                    pages_details_agg = []
                    for s in all_stats:
                        pages_details_agg.extend(s.get("pages_details") or [])
                    collected_reviews_agg = []
                    for s in all_stats:
                        collected_reviews_agg.extend(s.get("collected_reviews") or [])
                    success_all = all([(not s.get("errors")) for s in all_stats])
                    stats = {
                        "asin": "batch",
                        "total_reviews": total_reviews_sum,
                        "total_pages": total_pages_sum,
                        "errors": errors_agg,
                        "success": success_all,
                        "pages_details": pages_details_agg,
                        "total_reviews_header": None,
                        "product_global_review_count": None,
                        "persisted": all_stats[0].get("persisted") if all_stats else bool(persist),
                        "collected_reviews": collected_reviews_agg,
                        "full_pagination": bool(full_pagination),
                    }
                elif multi_tranches:
                    # exécuter 5→1 étoiles
                    sequence = ["five_star","four_star","three_star","two_star","one_star"]
                    all_stats = []
                    for sf in sequence:
                        st.info(f"Tranche en cours: {sf.replace('_',' ').title()}")
                        s = _run_one(sf)
                        all_stats.append(s)
                    # Fusion minimale des stats pour affichage (cumuls)
                    # Fusion sûre sans générateurs nus (compatibilité Syntax)
                    total_reviews_sum = sum([s.get("total_reviews", 0) for s in all_stats])
                    total_pages_sum = sum([s.get("total_pages", 0) for s in all_stats])
                    errors_agg = []
                    for s in all_stats:
                        errors_agg.extend(s.get("errors") or [])
                    pages_details_agg = []
                    for s in all_stats:
                        pages_details_agg.extend(s.get("pages_details") or [])
                    collected_reviews_agg = []
                    for s in all_stats:
                        collected_reviews_agg.extend(s.get("collected_reviews") or [])
                    success_all = all([(not s.get("errors")) for s in all_stats])
                    stats = {
                        "asin": asin,
                        "total_reviews": total_reviews_sum,
                        "total_pages": total_pages_sum,
                        "errors": errors_agg,
                        "success": success_all,
                        "pages_details": pages_details_agg,
                        "total_reviews_header": all_stats[0].get("total_reviews_header"),
                        "product_global_review_count": all_stats[0].get("product_global_review_count"),
                        "persisted": all_stats[0].get("persisted"),
                        "collected_reviews": collected_reviews_agg,
                        "full_pagination": full_pagination,
                    }
                else:
                    stats = _run_one(star_map.get(star_choice))
            # Affichage récapitulatif clair pour utilisateur novice
            st.markdown("### Résultat")
            status_msg_ok = f"✅ Terminé: {stats.get('total_reviews',0)} avis sur {stats.get('total_pages',0)} pages"
            status_msg_warn = f"⚠ Terminé avec erreurs: {len(stats.get('errors', []))} erreurs"
            if stats.get("success"):
                st.success(status_msg_ok)
            else:
                st.warning(status_msg_warn)

            # Détails par page
            pages_details = stats.get("pages_details") or []
            if pages_details:
                df_pages = pd.DataFrame(pages_details)
                # Ajouter contexte ASIN et libellé tranche étoiles
                if "asin" not in df_pages.columns:
                    df_pages["asin"] = asin
                # Domaine et URL produit canonique pour chaque ligne
                try:
                    if "domain" not in df_pages.columns:
                        df_pages["domain"] = (domain or "").strip() or (parsed.get("domain") if 'parsed' in locals() and parsed else "") or "www.amazon.fr"
                    df_pages["canonical_product_url"] = df_pages.apply(lambda r: generate_product_url(str(r.get("asin")), domain=str(r.get("domain") or "www.amazon.fr")), axis=1)
                except Exception:
                    pass
                star_map_labels = {
                    "five_star": "5 étoiles",
                    "four_star": "4 étoiles",
                    "three_star": "3 étoiles",
                    "two_star": "2 étoiles",
                    "one_star": "1 étoile",
                    None: "Toutes",
                }
                if "star_filter" in df_pages.columns:
                    df_pages["star_label"] = df_pages["star_filter"].map(star_map_labels).fillna("Toutes")
                else:
                    df_pages["star_label"] = "Toutes"
                # Colonnes affichées enrichies
                cols_order = [c for c in ["asin", "domain", "canonical_product_url", "star_label", "page", "reviews_parsed", "saved", "duration_s", "next", "error"] if c in df_pages.columns]
                df_pages = df_pages[cols_order]
                st.markdown("#### Détail par page")
                st.dataframe(df_pages, use_container_width=True)
                # Persister dans la session
                st.session_state["last_run"]["pages_df"] = df_pages.copy()

                # Récap batch par ASIN et tranche d'étoiles
                try:
                    grp_cols = [c for c in ["asin", "domain", "star_label"] if c in df_pages.columns]
                    if grp_cols:
                        df_recap = (
                            df_pages
                            .groupby(grp_cols, dropna=False)
                            .agg(pages=("page", "max"), reviews_parsed=("reviews_parsed", "sum"), saved=("saved", "sum"))
                            .reset_index()
                        )
                        # Ordonner 5→1 étoiles de façon lisible
                        star_order = ["5 étoiles", "4 étoiles", "3 étoiles", "2 étoiles", "1 étoile", "Toutes"]
                        if "star_label" in df_recap.columns:
                            df_recap["star_label"] = pd.Categorical(df_recap["star_label"], categories=star_order, ordered=True)
                            df_recap = df_recap.sort_values(["asin", "domain", "star_label"]).reset_index(drop=True)
                        st.markdown("#### Récap par ASIN / Domaine / Tranche d'étoiles (5→1)")
                        st.dataframe(df_recap, use_container_width=True)
                except Exception:
                    pass

                # Indicateur pagination complète + totaux
                try:
                    last_next = bool(df_pages.iloc[-1]["next"]) if not df_pages.empty and "next" in df_pages.columns else None
                    total_pages = int(stats.get("total_pages") or len(df_pages))
                    asked_pages = int(max_pages)
                    is_complete = (total_pages == asked_pages) or (last_next is False)
                    total_hdr = stats.get("total_reviews_header")
                    total_global = stats.get("product_global_review_count")
                    extra = []
                    if total_hdr:
                        extra.append(f"Total en-tête: {int(total_hdr)}")
                    if total_global:
                        extra.append(f"Évaluations globales produit: {int(total_global)}")
                    suffix = (" • " + " • ".join(extra)) if extra else ""
                    st.caption(
                        f"Pagination: {total_pages}/{asked_pages} pages • "
                        + ("✅ complète" if is_complete else "⚠ incomplète")
                        + suffix
                    )
                except Exception:
                    pass

                # Export du détail de pagination
                csv_pages = df_pages.to_csv(index=False).encode("utf-8")
                st.download_button("Exporter le détail de pagination (CSV)", data=csv_pages, file_name=f"pages_details_{asin}.csv", mime="text/csv")

            # Derniers avis insérés (aperçu)
            try:
                recent = scraper.get_reviews_for_asin(asin, limit=10)
                if recent:
                    st.markdown("#### 10 derniers avis")
                    st.table(pd.DataFrame(recent)[[c for c in ["review_id","review_date","rating","title","body"] if c in recent[0]]])
            except Exception:
                pass

            # Prévisualisation complète triée par sentiment + export (dédup revue par ID et par contenu)
            try:
                import hashlib
                from app.normalize import clean_text
                # Source des données: en mémoire (mode éphémère) ou base (persistant)
                if (not stats.get("persisted")) and stats.get("collected_reviews"):
                    all_reviews = pd.DataFrame(stats["collected_reviews"])
                else:
                    all_reviews = pd.DataFrame(scraper.get_reviews_for_asin(asin))
                if not all_reviews.empty:
                    # Dédoublonnage toujours actif côté aperçu (cohérent avec backend)
                    # 1) Dédoublonnage par review_id
                    if "review_id" in all_reviews.columns:
                        all_reviews = all_reviews.drop_duplicates(subset=["review_id"], keep="first")
                    # 2) Dédoublonnage par contenu canonique (titre+corps nettoyés)
                    def _canonical_key(row):
                        title = clean_text(str(row.get("review_title", "") or ""))
                        body = clean_text(str(row.get("review_body", "") or ""))
                        if title or body:
                            base = f"{title}|{body}".encode("utf-8")
                        else:
                            # Fallback stable si pas de texte: auteur+date+note+variante
                            author = clean_text(str(row.get("reviewer_name", "") or ""))
                            date = str(row.get("review_date", "") or "")
                            rating = str(row.get("rating", "") or "")
                            variant = clean_text(str(row.get("variant", "") or ""))
                            base = f"{author}|{date}|{rating}|{variant}".encode("utf-8")
                        return hashlib.sha1(base).hexdigest()
                    all_reviews["_canonical_key"] = all_reviews.apply(_canonical_key, axis=1)
                    all_reviews = all_reviews.drop_duplicates(subset=["_canonical_key"], keep="first").drop(columns=["_canonical_key"]) 
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
                    all_reviews["sentiment"] = all_reviews.get("rating", 0).apply(_sentiment_from_rating)
                    st.markdown("#### Aperçu des données (tri par sentiment)")
                    order = ["Positif", "Neutre", "Négatif"]
                    all_reviews["sentiment"] = pd.Categorical(all_reviews["sentiment"], categories=order, ordered=True)
                    all_reviews = all_reviews.sort_values(["sentiment", "review_date"], ascending=[True, False])
                    st.dataframe(all_reviews, use_container_width=True)
                    # Persister le DataFrame complet pour export ultérieur
                    st.session_state["last_run"]["reviews_df"] = all_reviews.copy()

                    col1, col2 = st.columns(2)
                    with col1:
                        csv_bytes = all_reviews.to_csv(index=False).encode("utf-8")
                        st.download_button("Télécharger CSV (trié)", data=csv_bytes, file_name=f"reviews_{asin}.csv", mime="text/csv")
                    with col2:
                        try:
                            import io
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                                all_reviews.to_excel(writer, index=False, sheet_name="reviews")
                            st.download_button("Télécharger Excel", data=output.getvalue(), file_name=f"reviews_{asin}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
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
    asin_filter = st.text_input("Filtrer par ASIN (optionnel)")
    limit = st.number_input("Limiter le nombre d'avis (optionnel)", min_value=0, max_value=10000, value=0)
    colx1, colx2 = st.columns(2)
    with colx1:
        do_export_session = st.button("Exporter le dernier run (session)")
    with colx2:
        do_export_db = st.button("Exporter depuis la base")

    # Export depuis le cache de session (ne provoque pas de nouveau run)
    if do_export_session:
        df = st.session_state.get("last_run", {}).get("reviews_df")
        if df is None or df.empty:
            st.warning("Aucun résultat en session. Lancez un run dans l'onglet Scraper.")
        else:
            st.download_button("Télécharger CSV (session)", data=df.to_csv(index=False).encode("utf-8"), file_name="reviews_session.csv", mime="text/csv")

    # Export depuis la base (peut être coûteux, mais ne redémarre pas le scraper)
    if do_export_db:
        scraper = AmazonScraper()
        lim = int(limit) if limit > 0 else None
        data = scraper.get_reviews_for_asin(asin_filter, lim) if asin_filter else scraper.get_all_reviews(lim)
        if not data:
            st.info("Aucun avis en base.")
        else:
            df = pd.DataFrame(data)
            st.download_button("Télécharger CSV (base)", data=df.to_csv(index=False).encode("utf-8"), file_name="reviews_db.csv", mime="text/csv")

with tab3:
    st.subheader("Authentification Amazon")
    st.caption("Sélectionnez un site et une langue, puis ouvrez la fenêtre de connexion. La session est enregistrée et vérifiée pour ce domaine/langue.")

    session_state_path = getattr(settings, "storage_state_path", "./storage_state.json")
    if os.path.exists(session_state_path):
        st.success(f"Session trouvée: {session_state_path}")
    else:
        st.info("Aucune session enregistrée.")

    col_auth1, col_auth2 = st.columns(2)
    with col_auth1:
        auth_domain = st.selectbox(
            "Site Amazon",
            options=[
                "www.amazon.fr",
                "www.amazon.es",
                "www.amazon.it",
                "www.amazon.nl",
                "www.amazon.de",
                "www.amazon.co.uk",
            ],
            index=0,
        )
    with col_auth2:
        auth_language_override = st.checkbox("Forcer la langue (avancé)", value=False, key="auth_lang_override")
        if auth_language_override:
            auth_language = st.selectbox(
                "Langue",
                options=["fr_FR", "es_ES", "it_IT", "nl_NL", "de_DE", "en_GB"],
                index=0,
            )
        else:
            # dériver automatiquement
            def _derive_lang(d: str) -> str:
                d = d.lower()
                if d.endswith(".fr"): return "fr_FR"
                if d.endswith(".es"): return "es_ES"
                if d.endswith(".it"): return "it_IT"
                if d.endswith(".nl"): return "nl_NL"
                if d.endswith(".de"): return "de_DE"
                if d.endswith(".co.uk"): return "en_GB"
                return "fr_FR"
            auth_language = _derive_lang(auth_domain)

    col_chk1, col_chk2 = st.columns(2)
    with col_chk1:
        if st.button("Vérifier la session (site/langue)"):
            with st.spinner("Vérification de la session sur le domaine sélectionné..."):
                ok = run_async(AmazonFetcher().check_session_valid_for(auth_domain, auth_language))
                if ok:
                    st.success(f"Session valide pour {auth_domain} ({auth_language}).")
                else:
                    st.warning(f"Session invalide pour {auth_domain} ({auth_language}). Veuillez vous connecter.")

    if st.button("Ouvrir la fenêtre de connexion Amazon"):
        with st.spinner("Ouverture de la fenêtre de connexion..."):
            old = settings.headless
            settings.headless = False
            async def run_login(timeout_sec: int = 600, domain: str = "www.amazon.fr", language: str = "fr_FR") -> bool:
                fetcher = AmazonFetcher()
                # Démarrer un navigateur sans storage_state pour éviter les collisions
                await fetcher.start_browser()
                # Forcer un contexte neuf sans storage_state pendant l'auth
                if fetcher.browser:
                    # Adapter locale/timezone de manière simple selon la langue
                    lang_locale = language.replace("_", "-")
                    tz = "Europe/Paris"
                    if domain.endswith(".uk"):
                        tz = "Europe/London"
                    elif domain.endswith(".es"):
                        tz = "Europe/Madrid"
                    elif domain.endswith(".de"):
                        tz = "Europe/Berlin"
                    elif domain.endswith(".it"):
                        tz = "Europe/Rome"
                    elif domain.endswith(".nl"):
                        tz = "Europe/Amsterdam"
                    context = await fetcher.browser.new_context(
                        user_agent=fetcher.ua_pool.get_random_ua(),
                        locale=lang_locale,
                        timezone_id=tz,
                        viewport={"width": 1280, "height": 900},
                    )  # type: ignore
                else:
                    context = await fetcher.create_context()
                page = await context.new_page()
                # Accueil FR puis navigation via header
                home_url = f"https://{domain}/"
                await page.set_extra_http_headers({"Accept-Language": language.replace("_", "-")})
                await page.goto(home_url, wait_until="domcontentloaded", timeout=settings.timeout_ms)
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
                    signin_url = f"https://{domain}/ap/signin?_encoding=UTF8"
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
                    # Sauvegarder l'état puis fermer proprement
                    await context.storage_state(path=session_state_path)
                await context.close()
                await fetcher.stop_browser()
                return logged
            ok = asyncio.run(run_login(domain=auth_domain, language=auth_language))
            settings.headless = old
            if ok:
                st.success(f"✓ Session enregistrée pour {auth_domain} ({auth_language}): {session_state_path}")
            else:
                st.error("Connexion non détectée dans le délai imparti.")

st.sidebar.header("Configuration rapide")
fast_mode = st.sidebar.checkbox("Mode rapide (optimisé)", value=False, help="Applique des préréglages rapides (pauses courtes, timeout réduit).")
headless = st.sidebar.checkbox("Headless (recommandé)", value=True)
pages_env = st.sidebar.number_input("Pages max par défaut", min_value=1, max_value=100, value=5)
sleep_min = st.sidebar.number_input("Pause min (s)", min_value=0.0, value=2.0)
sleep_max = st.sidebar.number_input("Pause max (s)", min_value=0.0, value=4.0)
timeout_ms_input = st.sidebar.number_input("Timeout (ms)", min_value=5000, max_value=120000, value=45000, step=1000)

if st.sidebar.button("Appliquer"):
    # Préréglages rapides
    if fast_mode:
        headless_val = True
        sleep_min_val = 0.2
        sleep_max_val = 0.6
        timeout_val = 25000
    else:
        headless_val = bool(headless)
        sleep_min_val = float(sleep_min)
        sleep_max_val = float(sleep_max)
        timeout_val = int(timeout_ms_input)

    # Applique à l'environnement courant (pour prochains runs/process)
    os.environ["HEADLESS"] = "true" if headless_val else "false"
    os.environ["MAX_PAGES_PER_ASIN"] = str(int(pages_env))
    os.environ["SLEEP_MIN"] = str(sleep_min_val)
    os.environ["SLEEP_MAX"] = str(sleep_max_val)
    os.environ["TIMEOUT_MS"] = str(timeout_val)

    # Applique immédiatement aux settings courants (sans redémarrer)
    try:
        settings.headless = headless_val
        settings.max_pages_per_asin = int(pages_env)
        settings.sleep_min = sleep_min_val
        settings.sleep_max = sleep_max_val
        settings.timeout_ms = timeout_val
    except Exception:
        pass
    st.sidebar.success("Configuration appliquée")

st.sidebar.markdown("---")
st.sidebar.write("Pour lancer:")
st.sidebar.code("streamlit run streamlit_app.py")


with tab4:
    st.subheader("Déduplication CSV (test)")
    st.caption("Chargez votre export (ex: 2025-10-01T15-27_export.csv). La déduplication applique la même logique que l'aperçu: par review_id, puis par contenu canonique (titre+corps normalisés).")

    uploaded = st.file_uploader("Fichier CSV", type=["csv"], accept_multiple_files=False)

    def _pick_col(df, candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    import hashlib
    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Impossible de lire le CSV: {e}")
            st.stop()

        rows_before = len(df)

        # 1) Dédoublonnage par review_id si présent
        id_col = _pick_col(df, ["review_id", "id"]) 
        if id_col:
            df = df.drop_duplicates(subset=[id_col], keep="first")

        # 2) Dédoublonnage par contenu canonique
        title_col = _pick_col(df, ["review_title", "title"]) or ""
        body_col = _pick_col(df, ["review_body", "body", "content", "text"]) or ""
        reviewer_col = _pick_col(df, ["reviewer_name", "author", "user"]) or ""
        date_col = _pick_col(df, ["review_date", "date"]) or ""
        rating_col = _pick_col(df, ["rating", "stars"]) or ""
        variant_col = _pick_col(df, ["variant"]) or ""

        def _canon_key(row):
            title = clean_text(str(row.get(title_col, "") if title_col else ""))
            body = clean_text(str(row.get(body_col, "") if body_col else ""))
            if title or body:
                base = f"{title}|{body}".encode("utf-8")
            else:
                author = clean_text(str(row.get(reviewer_col, "") if reviewer_col else ""))
                date = str(row.get(date_col, "") if date_col else "")
                rating = str(row.get(rating_col, "") if rating_col else "")
                variant = clean_text(str(row.get(variant_col, "") if variant_col else ""))
                base = f"{author}|{date}|{rating}|{variant}".encode("utf-8")
            return hashlib.sha1(base).hexdigest()

        df["_canonical_key"] = df.apply(_canon_key, axis=1)
        df = df.drop_duplicates(subset=["_canonical_key"], keep="first")
        rows_after = len(df)
        removed = rows_before - rows_after

        c1, c2, c3 = st.columns(3)
        c1.metric("Lignes avant", rows_before)
        c2.metric("Lignes après", rows_after)
        c3.metric("Doublons supprimés", removed)

        # Montrer quelques groupes doublonnés (s'il en reste, ce qui ne devrait pas)
        st.markdown("#### Échantillon (après dédup)")
        st.dataframe(df.head(200), use_container_width=True)

        st.download_button(
            "Télécharger CSV dédupliqué",
            data=df.drop(columns=["_canonical_key"]).to_csv(index=False).encode("utf-8"),
            file_name="export_dedup.csv",
            mime="text/csv",
        )
