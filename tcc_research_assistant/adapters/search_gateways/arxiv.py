import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List

from adapters.search_gateways.base_client import BaseSearchClient
from core.entities import Paper
from core.exceptions import NetworkError, RateLimitError

logger = logging.getLogger(__name__)


class ArxivClient(BaseSearchClient):
    BASE_URL = "http://export.arxiv.org/api/query"

    def search(
        self,
        query: str,
        max_results: int = 10,
        year_start: int = None,
        year_end: int = None,
    ) -> List[Paper]:
        self.http_client.rate_limiter.calls = 1
        self.http_client.rate_limiter.period = 3.0

        keywords = [k.strip() for k in query.split(",")]
        search_query = " OR ".join([f'all:"{k}"' for k in keywords])

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        papers: List[Paper] = []
        try:
            response = self.http_client.get(self.BASE_URL, params=params)
            response.raise_for_status()

            root = ET.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns).text.replace("\n", " ").strip()
                abstract = entry.find("atom:summary", ns).text.replace("\n", " ").strip()
                url = entry.find("atom:id", ns).text
                authors = [
                    author.find("atom:name", ns).text
                    for author in entry.findall("atom:author", ns)
                ]
                published = entry.find("atom:published", ns).text
                year = (
                    datetime.fromisoformat(published.replace("Z", "+00:00")).year
                    if published
                    else None
                )

                if year_start and year and year < year_start:
                    continue
                if year_end and year and year > year_end:
                    continue

                papers.append(
                    Paper(
                        title=title,
                        authors=authors,
                        year=year,
                        abstract=abstract,
                        url=url,
                        source="arXiv",
                        citations=0,
                    )
                )

        except (NetworkError, RateLimitError):
            raise
        except Exception as exc:
            logger.error("arXiv search failed: %s", exc, exc_info=True)

        return papers
