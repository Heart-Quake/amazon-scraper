"""Parser pour extraire les données des avis Amazon."""

import logging
import hashlib
from typing import Dict, List, Optional

from playwright.async_api import Page

from app.normalize import (
    clean_text,
    extract_review_id_from_url,
    normalize_date_fr,
    normalize_helpful_votes,
    normalize_rating,
    normalize_verified_purchase,
)
from app.selectors import ReviewSelectors

logger = logging.getLogger(__name__)

class ReviewParser:
    def __init__(self):
        self.selectors = ReviewSelectors.get_all_selectors()

    async def parse_review_block(self, page: Page, review_element) -> Optional[Dict]:
        try:
            review_data = await self._extract_basic_data(review_element)
            review_data.update(await self._extract_metadata(review_element))
            review_data.update(await self._extract_author_info(review_element))
            if not self._validate_review_data(review_data):
                return None
            return review_data
        except Exception as e:
            logging.getLogger(__name__).error(f"Erreur lors du parsing d'un avis: {e}")
            return None

    async def _extract_basic_data(self, review_element) -> Dict:
        data: Dict[str, object] = {}
        title_element = await review_element.query_selector(self.selectors["title"])
        if title_element:
            data["review_title"] = clean_text(await title_element.inner_text())
        body_element = await review_element.query_selector(self.selectors["body"])
        if body_element:
            data["review_body"] = clean_text(await body_element.inner_text())
        return data

    async def _extract_metadata(self, review_element) -> Dict:
        data: Dict[str, object] = {}
        rating_element = await review_element.query_selector(self.selectors["rating"])
        if rating_element:
            data["rating"] = normalize_rating(await rating_element.inner_text())
        date_element = await review_element.query_selector(self.selectors["date"])
        if date_element:
            data["review_date"] = normalize_date_fr(await date_element.inner_text())
        verified_element = await review_element.query_selector(self.selectors["verified"])
        if verified_element:
            data["verified_purchase"] = normalize_verified_purchase(await verified_element.inner_text())
        else:
            data["verified_purchase"] = False
        helpful_element = await review_element.query_selector(self.selectors["helpful"])
        if helpful_element:
            data["helpful_votes"] = normalize_helpful_votes(await helpful_element.inner_text())
        else:
            data["helpful_votes"] = 0
        return data

    async def _extract_author_info(self, review_element) -> Dict:
        data: Dict[str, object] = {}
        author_element = await review_element.query_selector(self.selectors["reviewer"])
        if author_element:
            data["reviewer_name"] = clean_text(await author_element.inner_text())
        variant_element = await review_element.query_selector(self.selectors["variant"])
        if variant_element:
            data["variant"] = clean_text(await variant_element.inner_text())
        return data

    def _validate_review_data(self, data: Dict) -> bool:
        has_content = bool(data.get("review_title") or data.get("review_body"))
        rating = data.get("rating")
        return has_content and (rating is None or (1.0 <= float(rating) <= 5.0))

    async def extract_review_id(self, review_element) -> Optional[str]:
        try:
            li_id = await review_element.get_attribute("id")
            if li_id and li_id.startswith("R"):
                return li_id
            inner = await review_element.query_selector('[id^="customer_review-"]')
            if inner:
                inner_id = await inner.get_attribute("id")
                if inner_id and "customer_review-" in inner_id:
                    return inner_id.split("customer_review-")[-1]
            link_element = await review_element.query_selector("a[href*='/reviews/']")
            if link_element:
                href = await link_element.get_attribute("href")
                if href:
                    return extract_review_id_from_url(href)
            # Fallback déterministe
            title_element = await review_element.query_selector(self.selectors["title"])
            body_element = await review_element.query_selector(self.selectors["body"])
            title = await title_element.inner_text() if title_element else ""
            body = await body_element.inner_text() if body_element else ""
            if title or body:
                text = f"{clean_text(title)}\n{clean_text(body)}".encode("utf-8")
                content_hash = hashlib.sha1(text).hexdigest()
                return f"generated_{content_hash}"
            return None
        except Exception as e:
            logging.getLogger(__name__).error(f"Erreur lors de l'extraction de l'ID d'avis: {e}")
            return None

    async def parse_reviews_from_page(self, page: Page) -> List[Dict]:
        reviews: List[Dict] = []
        selectors_chain = [
            self.selectors["block"],
            '#cm_cr-review_list [data-hook="review"]',
            'div#cm_cr-review_list div[data-hook="review"]',
            '[id^="customer_review-"]',
            'div[data-hook*="review"]',
            'div.a-section.review.aok-relative',
        ]
        review_elements = []
        last_error = None
        for _ in range(3):
            for sel in selectors_chain:
                try:
                    await page.wait_for_selector(sel, timeout=7000, state="attached")
                    review_elements = await page.query_selector_all(sel)
                    if review_elements:
                        self.selectors["block"] = sel
                        break
                except Exception as e:
                    last_error = e
                    continue
            if review_elements:
                break
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(800)
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(500)
            except Exception:
                pass
        if not review_elements:
            raise last_error or Exception("Aucun sélecteur d'avis n'a matché après scroll")
        seen_ids = set()
        for i, review_element in enumerate(review_elements):
            try:
                review_data = await self.parse_review_block(page, review_element)
                if not review_data:
                    continue
                review_id = await self.extract_review_id(review_element)
                if not review_id or review_id in seen_ids:
                    continue
                seen_ids.add(review_id)
                review_data["review_id"] = review_id
                reviews.append(review_data)
            except Exception:
                continue
        return reviews
