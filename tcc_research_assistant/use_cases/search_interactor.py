import concurrent.futures
import logging
import time
from typing import Callable, List, Optional

from adapters.repository.sqlite_cache import SQLiteCache
from adapters.search_gateways.base_client import BaseSearchClient
from core.entities import Paper
from core.exceptions import NetworkError, RateLimitError
from infrastructure.nlp_tools.processor import NLPProcessor
from use_cases.filter_engine import FilterEngine
from use_cases.ranking_engine import RankingEngine

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[int, str], None]]


class SearchInteractor:
    def __init__(
        self,
        clients: List[BaseSearchClient],
        cache: SQLiteCache,
        nlp: NLPProcessor,
        ranking: RankingEngine,
    ) -> None:
        self.clients = clients
        self.cache = cache
        self.nlp = nlp
        self.ranking = ranking
        self.filter_engine = FilterEngine()

    def execute_search(
        self,
        query: str,
        max_results: int = 10,
        year_start: int = None,
        year_end: int = None,
        lang_pref: str = "Todos",
        progress_callback: ProgressCallback = None,
    ) -> List[Paper]:
        def _notify(pct: int, msg: str) -> None:
            if progress_callback:
                progress_callback(pct, msg)

        total_clients = len(self.clients)
        all_papers: List[Paper] = []
        network_failures = 0

        _notify(10, f"Buscando em {total_clients} fonte(s)...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=total_clients) as executor:
            futures: dict = {}
            for i, client in enumerate(self.clients):
                if i > 0:
                    time.sleep(1.0)
                futures[
                    executor.submit(client.search, query, max_results, year_start, year_end)
                ] = client

            completed = 0
            for future in concurrent.futures.as_completed(futures):
                client = futures[future]
                client_name = client.__class__.__name__
                try:
                    papers = future.result()
                    all_papers.extend(papers)
                    logger.info("%s: %d artigo(s) encontrado(s).", client_name, len(papers))
                except (NetworkError, RateLimitError) as exc:
                    network_failures += 1
                    logger.warning("%s falhou: %s", client_name, exc)
                except Exception as exc:
                    logger.error("%s erro inesperado: %s", client_name, exc, exc_info=True)

                completed += 1
                # Progress: 10% → 50% as each source completes
                pct = 10 + int(completed / total_clients * 40)
                _notify(pct, f"Fonte concluída: {client_name}")

        if network_failures == total_clients and not all_papers:
            raise NetworkError(
                "Todas as fontes de busca falharam por problemas de rede ou bloqueio de IP."
            )

        _notify(55, "Deduplicando resultados...")
        unique_papers = self.cache.deduplicate(all_papers)
        for paper in unique_papers:
            self.cache.add_paper(paper)
        logger.info(
            "Deduplicação: %d → %d artigo(s) único(s).", len(all_papers), len(unique_papers)
        )

        _notify(62, "Aplicando filtros de ano e idioma...")
        filtered = self.filter_engine.filter_papers(unique_papers, lang_pref, year_start, year_end)
        logger.info("Após filtros: %d artigo(s).", len(filtered))

        _notify(72, "Processando linguagem natural (TF-IDF)...")
        processed = self.nlp.process_papers(query, filtered)

        _notify(85, "Calculando ranking de relevância...")
        ranked = self.ranking.rank_papers(query, processed)

        _notify(92, "Finalizando lista de resultados...")
        return ranked[:max_results]
