import logging
import os
import re
import time

from PySide6.QtCore import QThread, Signal

from core.exceptions import NetworkError, RateLimitError
from use_cases.search_interactor import SearchInteractor
from adapters.exporters.pdf_export import PDFExporter
from adapters.exporters.excel_export import ExcelExporter

logger = logging.getLogger(__name__)


class SearchWorker(QThread):
    progress_update = Signal(int, str)   # (percentage, stage_label)
    search_finished = Signal(dict)       # result payload
    search_error = Signal(str, str)      # (error_type, message)
    # error_type values: "network", "rate_limit", "generic"

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
            export_pdf = self.query_params.get("export_pdf", False)
            export_excel = self.query_params.get("export_excel", False)
            export_folder = self.query_params.get("export_folder")

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

            self.progress_update.emit(93, "Exportando arquivo...")
            exported_files = self._export(results, export_pdf, export_excel, export_folder)

            execution_time = time.time() - start_time
            self.progress_update.emit(100, "Concluído.")
            self.search_finished.emit(
                {
                    "papers": results,
                    "total": len(results),
                    "avg_sim": round(avg_sim, 4),
                    "time_sec": round(execution_time, 2),
                    "exported": exported_files,
                }
            )

        except NetworkError as exc:
            logger.error("Erro de rede na busca.", exc_info=True)
            self.search_error.emit("network", str(exc))
        except RateLimitError as exc:
            logger.warning("Rate limit atingido.", exc_info=True)
            self.search_error.emit("rate_limit", str(exc))
        except Exception as exc:
            logger.exception("Erro inesperado no SearchWorker.")
            self.search_error.emit("generic", str(exc))

    def _export(
        self,
        results: list,
        export_pdf: bool,
        export_excel: bool,
        export_folder: str,
    ) -> list[str]:
        if not (export_pdf or export_excel):
            return []

        if export_folder:
            os.makedirs(export_folder, exist_ok=True)

        next_num = self._next_file_number(export_folder or ".")
        base = f"{next_num}_Resultado_de_Pesquisa"
        exported = []

        if export_pdf:
            path = os.path.join(export_folder, f"{base}.pdf") if export_folder else f"{base}.pdf"
            exported.append(PDFExporter().export(results, path))

        if export_excel:
            path = os.path.join(export_folder, f"{base}.xlsx") if export_folder else f"{base}.xlsx"
            exported.append(ExcelExporter().export(results, path))

        return exported

    @staticmethod
    def _next_file_number(directory: str) -> int:
        next_num = 1
        if not os.path.exists(directory):
            return next_num
        for filename in os.listdir(directory):
            match = re.match(r"^(\d+)_Resultado_de_Pesquisa\.(pdf|xlsx)$", filename)
            if match:
                num = int(match.group(1))
                if num >= next_num:
                    next_num = num + 1
        return next_num
