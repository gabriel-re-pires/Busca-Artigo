import html
import json
import logging
import os
import re

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from adapters.exporters.excel_export import ExcelExporter
from adapters.exporters.pdf_export import PDFExporter
from infrastructure.gui.viewmodels.main_viewmodel import SearchWorker, format_source_report
from use_cases.search_interactor import SearchInteractor

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "pt": "Português",
    "en": "Inglês",
    "es": "Espanhol",
    "fr": "Francês",
    "de": "Alemão",
    "unknown": "—",
}


class _NumericItem(QTableWidgetItem):
    """Table item that sorts by its numeric value (Qt.UserRole) instead of text."""

    def __lt__(self, other):
        return (self.data(Qt.UserRole) or 0) < (other.data(Qt.UserRole) or 0)


class AppWindow(QMainWindow):
    def __init__(
        self,
        all_clients_map: dict,
        cache,
        nlp,
        ranking,
        icon_path: str = "",
        config_path: str = "config.json",
    ) -> None:
        super().__init__()

        # Injected dependencies — no construction here
        self.all_clients_map = all_clients_map
        self.cache = cache
        self.nlp = nlp
        self.ranking = ranking
        self.config_path = config_path
        self.last_papers: list = []  # resultados da última busca, para exportação sob demanda

        self.setWindowTitle("Busca-Artigo")
        self.resize(1050, 750)

        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._init_ui()
        self.showMaximized()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.setCentralWidget(scroll)

        central = QWidget()
        scroll.setWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        # --- Cards row ---
        cards = QHBoxLayout()
        cards.setSpacing(20)
        cards.addWidget(self._build_source_card())
        cards.addWidget(self._build_filter_card())
        cards.addWidget(self._build_export_card())
        root.addLayout(cards)

        # --- Search input (posicionado logo acima do botão de busca) ---
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText(
            "🔍 Digite palavras-chave separadas por vírgula e pressione Enter..."
        )
        self.kw_input.setMinimumHeight(55)
        self.kw_input.setClearButtonEnabled(True)
        self.kw_input.returnPressed.connect(self._start_search)
        self.kw_input.setFocus()
        root.addWidget(self.kw_input)

        # --- Search button ---
        self.btn_search = QPushButton("Iniciar Busca")
        self.btn_search.setObjectName("PrimaryButton")
        self.btn_search.setCursor(Qt.PointingHandCursor)
        self.btn_search.setMinimumHeight(55)
        self.btn_search.clicked.connect(self._start_search)
        root.addWidget(self.btn_search)

        # --- Progress area ---
        prog_row = QHBoxLayout()
        self.progress_label = QLabel("Pronto.")
        self.progress_label.setObjectName("StatusText")
        self.progress_percent = QLabel("0%")
        self.progress_percent.setObjectName("StatusText")
        self.progress_percent.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        prog_row.addWidget(self.progress_label)
        prog_row.addWidget(self.progress_percent)
        root.addLayout(prog_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        root.addWidget(self.progress_bar)

        # --- Stats ---
        self.stats_label = QLabel("Total: 0 | Semelh. Média: 0.00 | Tempo: 0s")
        self.stats_label.setObjectName("StatsText")
        root.addWidget(self.stats_label)

        # --- Status por fonte (mostra se cada base respondeu) ---
        self.sources_label = QLabel("")
        self.sources_label.setObjectName("StatusText")
        self.sources_label.setWordWrap(True)
        self.sources_label.setVisible(False)
        root.addWidget(self.sources_label)

        # --- Results table ---
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["#", "Relevância", "Semelh.", "Título", "Autores", "Ano", "Citações", "Idioma", "Fonte"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setWordWrap(True)
        self.table.cellDoubleClicked.connect(self._open_paper_url)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        for col in (0, 1, 2, 5, 6, 7, 8):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        root.addWidget(self.table)

        # --- Hint (shown after results arrive) ---
        self.hint_label = QLabel(
            "💡 Duplo clique em um artigo para abri-lo no navegador  ·  "
            "Passe o mouse sobre o título para ver o resumo  ·  "
            "Clique nos cabeçalhos para ordenar"
        )
        self.hint_label.setObjectName("StatusText")
        self.hint_label.setVisible(False)
        root.addWidget(self.hint_label)

    def _build_source_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("CardFrame")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel(" Fontes de Pesquisa")
        title.setObjectName("CardTitle")
        layout.addWidget(title)

        self.chk_scholar = QCheckBox("Google Scholar")
        self.chk_scholar.setChecked(True)
        self.chk_arxiv = QCheckBox("arXiv")
        self.chk_arxiv.setChecked(True)
        self.chk_semantic = QCheckBox("Semantic Scholar")
        self.chk_semantic.setChecked(True)
        self.chk_ieee = QCheckBox("IEEE Xplore")  # Placeholder — not yet implemented
        self.chk_ieee.setChecked(False)
        self.chk_ieee.setEnabled(False)

        for chk in (self.chk_scholar, self.chk_arxiv, self.chk_semantic, self.chk_ieee):
            layout.addWidget(chk)

        layout.addStretch()
        return card

    def _build_filter_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("CardFrame")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel(" Filtros de Busca")
        title.setObjectName("CardTitle")
        layout.addWidget(title)

        lang_label = QLabel("Idioma Preferencial:")
        lang_label.setStyleSheet("font-weight: bold;")
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["Todos", "Português", "Inglês"])
        layout.addWidget(lang_label)
        layout.addWidget(self.combo_lang)

        max_res_label = QLabel("Quantidade Máxima de Resultados:")
        max_res_label.setStyleSheet("font-weight: bold;")
        self.spin_max_res = QSpinBox()
        self.spin_max_res.setRange(10, 500)
        self.spin_max_res.setValue(100)
        layout.addWidget(max_res_label)
        layout.addWidget(self.spin_max_res)

        year_row = QHBoxLayout()
        self.year_start_input = QLineEdit()
        self.year_start_input.setPlaceholderText("Ano Inicial")
        self.year_end_input = QLineEdit()
        self.year_end_input.setPlaceholderText("Até")
        year_row.addWidget(self.year_start_input)
        year_row.addWidget(self.year_end_input)
        layout.addLayout(year_row)

        layout.addStretch()
        return card

    def _build_export_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("CardFrame")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel(" Opções de Exportação")
        title.setObjectName("CardTitle")
        layout.addWidget(title)

        self.radio_pdf = QRadioButton("Exportar para PDF")
        self.radio_excel = QRadioButton("Exportar para Planilha Excel")
        self.radio_excel.setChecked(True)
        self.export_group = QButtonGroup(self)
        self.export_group.addButton(self.radio_pdf)
        self.export_group.addButton(self.radio_excel)
        layout.addWidget(self.radio_pdf)
        layout.addWidget(self.radio_excel)

        dir_label = QLabel("Pasta de Destino dos Resultados:")
        dir_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(dir_label)

        self.current_export_dir = self._load_export_dir()
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        self.dir_input.setText(self.current_export_dir)

        self.btn_select_dir = QPushButton("Selecionar Pasta")
        self.btn_select_dir.setCursor(Qt.PointingHandCursor)
        self.btn_select_dir.clicked.connect(self._select_export_folder)

        dir_row = QHBoxLayout()
        dir_row.addWidget(self.dir_input)
        dir_row.addWidget(self.btn_select_dir)
        layout.addLayout(dir_row)

        layout.addStretch()

        # Botão de exportação sob demanda — só salva quando clicado
        self.btn_export = QPushButton("Exportar")
        self.btn_export.setObjectName("ExportButton")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setMinimumHeight(42)
        self.btn_export.setEnabled(False)  # habilita só quando houver resultados
        self.btn_export.setToolTip("Realize uma busca para habilitar a exportação.")
        self.btn_export.clicked.connect(self._on_export_clicked)
        layout.addWidget(self.btn_export)

        return card

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _load_export_dir(self) -> str:
        default = os.path.join(os.path.expanduser("~"), "Documents")
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                saved = cfg.get("export_directory", "")
                if saved and os.path.isdir(saved):
                    return saved
            except Exception:
                pass
        return default

    def _save_export_dir(self, folder: str) -> None:
        cfg: dict = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                pass
        cfg["export_directory"] = folder
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
        except Exception:
            logger.warning("Não foi possível salvar config.json.")

    def _select_export_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Selecionar Pasta de Exportação", self.current_export_dir
        )
        if folder:
            self.current_export_dir = folder
            self.dir_input.setText(folder)
            self._save_export_dir(folder)

    # ------------------------------------------------------------------
    # Search lifecycle
    # ------------------------------------------------------------------

    def _start_search(self) -> None:
        if not self.btn_search.isEnabled():  # search already running (e.g. Enter pressed again)
            return

        query = self.kw_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Aviso", "Por favor, insira pelo menos uma palavra-chave.")
            return

        active_clients = []
        if self.chk_arxiv.isChecked():
            active_clients.append(self.all_clients_map["arXiv"])
        if self.chk_scholar.isChecked():
            active_clients.append(self.all_clients_map["Google Scholar"])
        if self.chk_semantic.isChecked():
            active_clients.append(self.all_clients_map["Semantic Scholar"])

        if not active_clients:
            QMessageBox.warning(
                self, "Aviso", "Por favor, selecione pelo menos uma fonte de pesquisa."
            )
            return

        interactor = SearchInteractor(active_clients, self.cache, self.nlp, self.ranking)

        ys = self._parse_year(self.year_start_input.text())
        ye = self._parse_year(self.year_end_input.text())
        if ys and ys < 1990:
            ys = 1990

        params = {
            "query": query,
            "max_results": self.spin_max_res.value(),
            "year_start": ys,
            "year_end": ye,
            "lang_pref": self.combo_lang.currentText(),
        }

        self._set_searching_state(True)

        self.worker = SearchWorker(interactor, params)
        self.worker.progress_update.connect(self._update_progress)
        self.worker.search_finished.connect(self._on_search_finished)
        self.worker.search_error.connect(self._on_search_error)
        self.worker.start()

    def _update_progress(self, val: int, stage: str) -> None:
        self.progress_bar.setValue(val)
        self.progress_percent.setText(f"{val}%")
        self.progress_label.setText(stage)

    def _on_search_finished(self, payload: dict) -> None:
        self._set_searching_state(False)

        self.stats_label.setText(
            f"Total: {payload['total']} | "
            f"Semelh. Média: {payload['avg_sim']} | "
            f"Tempo: {payload['time_sec']}s"
        )
        self._show_source_report(payload.get("source_report"))

        papers = payload["papers"]
        self.last_papers = papers
        self.btn_export.setEnabled(bool(papers))
        self.btn_export.setToolTip(
            "Salvar os resultados no formato selecionado."
            if papers else "Realize uma busca para habilitar a exportação."
        )
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(papers))
        for row, p in enumerate(papers):
            self.table.setItem(row, 0, self._num_item(str(row + 1), row + 1))
            self.table.setItem(
                row, 1, self._num_item(f"{p.final_score * 100:.1f}%", p.final_score)
            )
            self.table.setItem(
                row, 2, self._num_item(f"{p.similarity_score * 100:.1f}%", p.similarity_score)
            )

            title_item = QTableWidgetItem(p.title)
            title_item.setData(Qt.UserRole, p.url)
            title_item.setToolTip(self._build_tooltip(p))
            self.table.setItem(row, 3, title_item)

            self.table.setItem(row, 4, QTableWidgetItem(", ".join(p.authors)))
            self.table.setItem(
                row, 5, self._num_item(str(p.year) if p.year else "—", p.year or 0)
            )
            self.table.setItem(row, 6, self._num_item(str(p.citations), p.citations))

            lang_item = QTableWidgetItem(
                LANGUAGE_NAMES.get(p.language, p.language.capitalize())
            )
            lang_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 7, lang_item)

            source_item = QTableWidgetItem(p.source)
            source_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 8, source_item)

        self.table.setSortingEnabled(True)
        self.hint_label.setVisible(len(papers) > 0)
        self.table.resizeRowsToContents()
        table_h = (
            self.table.horizontalHeader().height()
            + self.table.verticalHeader().length()
            + self.table.frameWidth() * 2
        )
        self.table.setMinimumHeight(table_h)

        logger.info(
            "Busca concluída: %d resultado(s) em %.2fs.",
            payload["total"],
            payload["time_sec"],
        )

    def _on_search_error(self, error_type: str, message: str) -> None:
        self._set_searching_state(False)
        self.last_papers = []
        self.btn_export.setEnabled(False)

        if error_type == "empty":
            self.progress_label.setText("Nenhum resultado.")
            QMessageBox.information(
                self,
                "Nenhum Resultado Encontrado",
                f"{message}\n\n"
                "Sugestões:\n"
                "• Aguarde alguns minutos (fontes como arXiv e Semantic Scholar "
                "podem bloquear temporariamente por excesso de requisições).\n"
                "• Tente outras palavras-chave ou marque outras fontes.\n"
                "• Afrouxe os filtros de ano/idioma.",
            )
            return

        self.progress_label.setText("Ocorreu um erro.")

        if error_type == "network":
            QMessageBox.critical(
                self,
                "Erro de Conexão",
                f"Não foi possível conectar às fontes de busca.\n\n"
                f"{message}\n\n"
                "Verifique sua conexão com a internet e tente novamente.",
            )
        elif error_type == "rate_limit":
            QMessageBox.warning(
                self,
                "Limite de Requisições Atingido",
                f"Uma fonte de busca bloqueou o acesso temporariamente.\n\n"
                f"{message}\n\n"
                "Aguarde alguns minutos antes de realizar uma nova busca.",
            )
        else:
            QMessageBox.critical(
                self,
                "Erro Inesperado",
                f"Ocorreu um erro durante a busca:\n\n{message}",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _num_item(text: str, value) -> _NumericItem:
        """Center-aligned table item that sorts numerically."""
        item = _NumericItem(text)
        item.setData(Qt.UserRole, value)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    @staticmethod
    def _build_tooltip(paper) -> str:
        abstract = (paper.abstract or "").strip()
        if len(abstract) > 600:
            abstract = abstract[:600].rsplit(" ", 1)[0] + "…"
        body = html.escape(abstract) if abstract else "<i>Resumo não disponível.</i>"
        return (
            f"<p style='white-space:normal; width:480px;'>"
            f"<b>{html.escape(paper.title)}</b><br/><br/>{body}<br/><br/>"
            f"<i>🖱️ Duplo clique para abrir no navegador</i></p>"
        )

    def _open_paper_url(self, row: int, _col: int) -> None:
        item = self.table.item(row, 3)
        if item is None:
            return
        url = item.data(Qt.UserRole)
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _show_source_report(self, report: dict) -> None:
        """Mostra, abaixo das estatísticas, o que cada fonte retornou."""
        if not report:
            self.sources_label.setVisible(False)
            return
        parts = [f"{name}: {status}" for name, status in report.items()]
        self.sources_label.setText("Fontes  →   " + "    |    ".join(parts))
        self.sources_label.setVisible(True)

    # ------------------------------------------------------------------
    # Export (sob demanda — só ao clicar em "Exportar")
    # ------------------------------------------------------------------

    def _on_export_clicked(self) -> None:
        if not self.last_papers:
            QMessageBox.warning(
                self, "Aviso", "Não há resultados para exportar. Realize uma busca primeiro."
            )
            return

        folder = os.path.join(self.current_export_dir, "Resultados_Busca-Artigo")
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                self, "Erro", f"Não foi possível criar a pasta de destino:\n{exc}"
            )
            return

        want_pdf = self.radio_pdf.isChecked()
        want_excel = self.radio_excel.isChecked()

        self.btn_export.setEnabled(False)
        self.btn_export.setText("Exportando...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        exported: list = []
        try:
            exported = self._export_results(self.last_papers, folder, want_pdf, want_excel)
        except Exception as exc:
            logger.exception("Falha na exportação.")
            QMessageBox.critical(
                self, "Erro na Exportação", f"Não foi possível exportar os resultados:\n\n{exc}"
            )
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_export.setText("Exportar")
            self.btn_export.setEnabled(True)

        if exported:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("Exportação Concluída")
            msg_box.setText("Exportação concluída com sucesso:\n" + "\n".join(exported))
            open_btn = msg_box.addButton("Abrir Pasta", QMessageBox.ActionRole)
            msg_box.addButton(QMessageBox.Ok)
            msg_box.exec()
            if msg_box.clickedButton() == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(exported[0])))

    def _export_results(
        self, papers: list, folder: str, want_pdf: bool, want_excel: bool
    ) -> list:
        next_num = self._next_file_number(folder)
        base = f"{next_num}_Resultado_de_Pesquisa"
        exported = []
        if want_pdf:
            exported.append(PDFExporter().export(papers, os.path.join(folder, f"{base}.pdf")))
        if want_excel:
            exported.append(ExcelExporter().export(papers, os.path.join(folder, f"{base}.xlsx")))
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

    def _set_searching_state(self, searching: bool) -> None:
        self.btn_search.setEnabled(not searching)
        self.btn_search.setText("Buscando..." if searching else "Iniciar Busca")
        if searching:
            self.progress_bar.setValue(0)
            self.progress_percent.setText("0%")
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            self.hint_label.setVisible(False)
            self.sources_label.setVisible(False)
            self.btn_export.setEnabled(False)

    @staticmethod
    def _parse_year(text: str):
        try:
            return int(text.strip()) if text.strip() else None
        except ValueError:
            return None
