import logging
import time

from PySide6.QtCore import QThread, Signal

from core.exceptions import EmptyResultsError, NetworkError, RateLimitError
from use_cases.search_interactor import SearchInteractor

logger = logging.getLogger(__name__)


def format_source_report(report: dict) -> str:
    """Turns {'arXiv': '5 resultado(s)', ...} into a readable multi-line string."""
    if not report:
        return ""
    return "\n".join(f"  • {name}: {status}" for name, status in report.items())


class SearchWorker(QThread):
    progress_update = Signal(int, str)   # (percentage, stage_label)
    search_finished = Signal(dict)       # result payload
    search_error = Signal(str, str)      # (error_type, message)
    # error_type values: "network", "rate_limit", "empty", "generic"

    def __init__(self, interactor: SearchInteractor, query_params: dict) -> None:
        super().__init__()
        self.interactor = interactor
        self.query_params = query_params

    def run(self) -> None:
        start_time = time.time()
        try:
            self.progress_update.emit(5, "Preparando busca...")

            query = self.query_params.get("query", "")
            max_res = self.query_params.get("max_results", 10)
            y_start = self.query_params.get("year_start")
            y_end = self.query_params.get("year_end")
            lang_pref = self.query_params.get("lang_pref", "Todos")

            # The interactor drives progress from 10% → 92%
            def on_progress(pct: int, msg: str) -> None:
                self.progress_update.emit(pct, msg)

            results = self.interactor.execute_search(
                query, max_res, y_start, y_end, lang_pref,
                progress_callback=on_progress,
            )

            avg_sim = 0.0
            if results:
                avg_sim = sum(p.similarity_score for p in results) / len(results)

            execution_time = time.time() - start_time
            self.progress_update.emit(100, "Concluído.")
            self.search_finished.emit(
                {
                    "papers": results,
                    "total": len(results),
                    "avg_sim": round(avg_sim, 4),
                    "time_sec": round(execution_time, 2),
                    "source_report": dict(self.interactor.source_report),
                }
            )

        except EmptyResultsError as exc:
            logger.info("Busca sem resultados: %s", exc)
            report = format_source_report(exc.source_report)
            message = str(exc)
            if report:
                message += "\n\nStatus de cada fonte:\n" + report
            self.search_error.emit("empty", message)
        except NetworkError as exc:
            logger.error("Erro de rede na busca.", exc_info=True)
            self.search_error.emit("network", str(exc))
        except RateLimitError as exc:
            logger.warning("Rate limit atingido.", exc_info=True)
            self.search_error.emit("rate_limit", str(exc))
        except Exception as exc:
            logger.exception("Erro inesperado no SearchWorker.")
            self.search_error.emit("generic", str(exc))
