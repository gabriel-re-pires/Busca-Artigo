import concurrent.futures
import logging
import time
from typing import Callable, List, Optional

from adapters.repository.sqlite_cache import SQLiteCache
from adapters.search_gateways.base_client import BaseSearchClient
from core.entities import Paper
from core.exceptions import EmptyResultsError, NetworkError, RateLimitError
from infrastructure.nlp_tools.processor import NLPProcessor
from use_cases.filter_engine import FilterEngine
from use_cases.ranking_engine import RankingEngine

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[int, str], None]]

# Nomes amigáveis para exibir no relatório por fonte (classe -> rótulo)
_FRIENDLY_NAMES = {
    "ArxivClient": "arXiv",
    "ScholarClient": "Google Scholar",
    "SemanticScholarClient": "Semantic Scholar",
}


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
        # Preenchido a cada busca: {nome_da_fonte: status legível}
        self.source_report: dict = {}

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
        self.source_report = {}

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
                cls_name = client.__class__.__name__
                name = _FRIENDLY_NAMES.get(cls_name, cls_name)
                try:
                    papers = future.result()
                    all_papers.extend(papers)
                    if papers:
                        self.source_report[name] = f"{len(papers)} resultado(s)"
                    else:
                        self.source_report[name] = "sem resultados (0)"
                    logger.info("%s: %d artigo(s) encontrado(s).", name, len(papers))
                except RateLimitError as exc:
                    network_failures += 1
                    self.source_report[name] = "bloqueado (muitas requisições — HTTP 429)"
                    logger.warning("%s bloqueado: %s", name, exc)
                except NetworkError as exc:
                    network_failures += 1
                    self.source_report[name] = "falha de conexão"
                    logger.warning("%s falhou: %s", name, exc)
                except Exception as exc:
                    self.source_report[name] = "erro ao processar a resposta"
                    logger.error("%s erro inesperado: %s", name, exc, exc_info=True)

                completed += 1
                # Progress: 10% → 50% as each source completes
                pct = 10 + int(completed / total_clients * 40)
                _notify(pct, f"Fonte concluída: {name}")

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

        if not ranked:
            # Nunca retorna vazio em silêncio: explica o porquê.
            if not all_papers:
                msg = "Nenhuma fonte retornou artigos para esta busca."
            elif not filtered:
                msg = (
                    "As fontes retornaram artigos, mas todos foram descartados pelos "
                    "filtros de ano/idioma. Tente afrouxar os filtros."
                )
            else:
                msg = "Não foi possível montar a lista de resultados."
            raise EmptyResultsError(msg, dict(self.source_report))

        return ranked[:max_results]
