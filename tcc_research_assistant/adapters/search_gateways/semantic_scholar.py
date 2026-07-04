import logging
from typing import List

from adapters.search_gateways.base_client import BaseSearchClient
from core.entities import Paper
from core.exceptions import NetworkError, RateLimitError

logger = logging.getLogger(__name__)


class SemanticScholarClient(BaseSearchClient):
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def search(
        self,
        query: str,
        max_results: int = 10,
        year_start: int = None,
        year_end: int = None,
    ) -> List[Paper]:
        # 100 requests per 5 minutes without API key
        self.http_client.rate_limiter.calls = 100
        self.http_client.rate_limiter.period = 300.0

        year_range = ""
        if year_start and year_end:
            year_range = f"{year_start}-{year_end}"
        elif year_start:
            year_range = f"{year_start}-"
        elif year_end:
            year_range = f"-{year_end}"

        params = {
            "query": query.replace(",", " "),
            "limit": max_results,
            "fields": "title,authors,year,abstract,url,citationCount,externalIds,publicationTypes",
        }
        if year_range:
            params["year"] = year_range

        papers: List[Paper] = []
        try:
            response = self.http_client.get(self.BASE_URL, params=params)
            response.raise_for_status()

            data = response.json()
            for item in data.get("data", []):
                authors = [a.get("name") for a in item.get("authors", [])]
                doi = item.get("externalIds", {}).get("DOI")
                ptypes = item.get("publicationTypes")

                classification = "unknown"
                if ptypes and isinstance(ptypes, list):
                    classification = ptypes[0]

                url = item.get("url") or (f"https://doi.org/{doi}" if doi else "")

                papers.append(
                    Paper(
                        title=item.get("title", ""),
                        authors=authors,
                        year=item.get("year"),
                        abstract=item.get("abstract") or "",
                        url=url,
                        source="Semantic Scholar",
                        citations=item.get("citationCount", 0),
                        doi=doi,
                        classification=classification,
                    )
                )

        except (NetworkError, RateLimitError):
            raise
        except Exception as exc:
            logger.error("Semantic Scholar search failed: %s", exc, exc_info=True)

        return papers
