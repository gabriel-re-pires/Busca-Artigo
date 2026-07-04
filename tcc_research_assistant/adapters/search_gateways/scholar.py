import logging
import re
from typing import List

from bs4 import BeautifulSoup

from adapters.search_gateways.base_client import BaseSearchClient
from core.entities import Paper
from core.exceptions import NetworkError, RateLimitError

logger = logging.getLogger(__name__)

_SCHOLAR_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class ScholarClient(BaseSearchClient):
    BASE_URL = "https://scholar.google.com/scholar"

    def search(
        self,
        query: str,
        max_results: int = 10,
        year_start: int = None,
        year_end: int = None,
    ) -> List[Paper]:
        # Strict rate limit to avoid CAPTCHA / IP bans
        self.http_client.rate_limiter.calls = 1
        self.http_client.rate_limiter.period = 15.0

        params = {"q": query.replace(",", " "), "hl": "en"}
        if year_start:
            params["as_ylo"] = year_start
        if year_end:
            params["as_yhi"] = year_end

        papers: List[Paper] = []
        try:
            response = self.http_client.get(
                self.BASE_URL,
                params=params,
                custom_headers={"User-Agent": _SCHOLAR_UA},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = soup.find_all("div", class_="gs_ri")

            for count, result in enumerate(results):
                if count >= max_results:
                    break

                title_el = result.find("h3", class_="gs_rt")
                title = title_el.text.strip() if title_el else "Unknown Title"
                url_el = title_el.find("a") if title_el else None
                url = url_el["href"] if url_el and "href" in url_el.attrs else ""

                author_info_el = result.find("div", class_="gs_a")
                author_info = author_info_el.text if author_info_el else ""

                year_match = re.search(r"\b(19|20)\d{2}\b", author_info)
                year = int(year_match.group(0)) if year_match else None

                authors = (
                    [a.strip() for a in author_info.split("-")[0].split(",")]
                    if "-" in author_info
                    else []
                )

                abstract_el = result.find("div", class_="gs_rs")
                abstract = abstract_el.text.strip() if abstract_el else ""

                citations = 0
                cit_el = result.find("a", string=re.compile(r"Cited by"))
                if cit_el:
                    cit_match = re.search(r"\d+", cit_el.text)
                    if cit_match:
                        citations = int(cit_match.group(0))

                papers.append(
                    Paper(
                        title=title,
                        authors=authors,
                        year=year,
                        abstract=abstract,
                        url=url,
                        source="Google Scholar",
                        citations=citations,
                    )
                )

        except (NetworkError, RateLimitError):
            raise
        except Exception as exc:
            logger.error(
                "Google Scholar search failed (possível CAPTCHA): %s", exc, exc_info=True
            )

        return papers
