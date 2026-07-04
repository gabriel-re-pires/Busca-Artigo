import logging
import os
import sys
from pathlib import Path


def get_resource_path(relative: str) -> str:
    """Resolve read-only bundled assets for both dev and PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(__file__), relative)


def get_writable_path(relative: str) -> str:
    """Resolve writable user-data paths (config, logs, DB).

    In a PyInstaller bundle the app directory is read-only (inside _MEIPASS),
    so writable files live next to the .exe instead.
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(os.path.dirname(sys.executable), relative)
    return os.path.join(os.path.dirname(__file__), relative)


def setup_logging() -> None:
    log_dir = Path(get_writable_path("logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_dir / "app.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_stylesheet(app, path: str) -> None:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Iniciando Busca-Artigo...")

    # Deferred imports ensure logging is fully configured before any module loads
    from PySide6.QtWidgets import QApplication
    from adapters.repository.sqlite_cache import SQLiteCache
    from adapters.search_gateways.arxiv import ArxivClient
    from adapters.search_gateways.scholar import ScholarClient
    from adapters.search_gateways.semantic_scholar import SemanticScholarClient
    from infrastructure.nlp_tools.processor import NLPProcessor
    from infrastructure.gui.app_window import AppWindow
    from use_cases.ranking_engine import RankingEngine

    # ── Composition Root ──────────────────────────────────────────────
    # Build the entire dependency graph here. Nothing is instantiated
    # inside AppWindow or the ViewModels — they receive what they need.
    cache = SQLiteCache(db_path=get_writable_path("research_cache.db"))
    nlp = NLPProcessor()
    ranking = RankingEngine()

    all_clients_map = {
        "arXiv": ArxivClient(),
        "Semantic Scholar": SemanticScholarClient(),
        "Google Scholar": ScholarClient(),
    }

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    load_stylesheet(app, get_resource_path("styles.qss"))

    window = AppWindow(
        all_clients_map=all_clients_map,
        cache=cache,
        nlp=nlp,
        ranking=ranking,
        icon_path=get_resource_path(os.path.join("assets", "icons", "logopag.ico")),
        config_path=get_writable_path("config.json"),
    )
    window.show()

    logger.info("Aplicação iniciada com sucesso.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
