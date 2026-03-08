import sys
import os
import logging
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSizePolicy, QSplitter
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, Slot, QThread, Signal
from PySide6.QtGui import QFont, QColor

from sqlmodel import Session, select
from src.infrastructure.database import engine, crear_base_datos_y_tablas
from src.domain.entities import DocumentoPrincipal
from src.domain.enums import FaseCicloVida
from src.domain.schemas import AnalisisDocumento
from src.infrastructure.document_analyzer import DocumentAnalyzerService
from src.infrastructure.ocr_processor import OcrProcessor
from src.infrastructure.network_storage import NetworkStorageManager
from src.presentation.documento_viewmodel import DocumentoViewModel
from src.infrastructure.config import Settings
from src.presentation.styles import AppStyles
from src.presentation.templates import RESULTADO_TEMPLATE

from dataclasses import dataclass

@dataclass(frozen=True)
class ButtonState:
    clasificar_enabled: bool
    clasificar_tooltip: str
    archivar_enabled: bool

class DocumentLoader(QThread):
    documents_loaded = Signal(list)
    error_occurred = Signal(str)
    
    def __init__(self, page: int = 1, page_size: int = 100):
        super().__init__()
        self.page = page
        self.page_size = page_size
    
    def run(self):
        try:
            with Session(engine) as session:
                statement = (
                    select(
                        DocumentoPrincipal.folio_oficial,
                        DocumentoPrincipal.remitente,
                        DocumentoPrincipal.asunto,
                        DocumentoPrincipal.fase_ciclo_vida
                    )
                    .order_by(DocumentoPrincipal.id.desc())
                    .offset((self.page - 1) * self.page_size)
                    .limit(self.page_size)
                )
                results = session.exec(statement).all()
                self.documents_loaded.emit(list(results))
        except Exception as e:
            self.error_occurred.emit(str(e))

class MainWindow(QMainWindow):
    FASE_CONFIG: dict[FaseCicloVida, ButtonState] = {
        FaseCicloVida.NACIMIENTO: ButtonState(False, "Cargue un documento primero", False),
        FaseCicloVida.INGRESADO: ButtonState(True, "Listo para clasificar", False),
        FaseCicloVida.CLASIFICADO: ButtonState(False, "El documento ya ha sido clasificado", True),
        FaseCicloVida.ARCHIVADO: ButtonState(False, "Documento ya archivado", False),
        FaseCicloVida.SELLADO: ButtonState(False, "Documento sellado", False),
        FaseCicloVida.RECHAZADO: ButtonState(False, "Documento rechazado", False),
    }

    def __init__(self, view_model: DocumentoViewModel) -> None:
        super().__init__()
        self.view_model = view_model
        
        self._setup_window_properties()
        self._build_ui()
        self._connect_signals()
        self._initialize_data()

    def _setup_window_properties(self) -> None:
        self.setWindowTitle("CADIDO - Gestión Documental Inteligente")
        self.resize(1024, 768)
        self.setMinimumSize(900, 650)

    def _build_ui(self) -> None:
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self._create_left_panel())
        self.splitter.addWidget(self._create_pdf_viewer())
        self.setCentralWidget(self.splitter)
        self.splitter.setSizes([400, 600])

    def _create_pdf_viewer(self) -> QWebEngineView:
        self.web_view = QWebEngineView()
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.PluginsEnabled, True)
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.PdfViewerEnabled, True)
        self.web_view.setMinimumWidth(500)
        return self.web_view

    def _create_left_panel(self) -> QWidget:
        widget = QWidget()
        layout_principal = QVBoxLayout(widget)
        layout_principal.setContentsMargins(30, 30, 30, 30)
        layout_principal.setSpacing(20)

        lbl_titulo = QLabel("Sistema de Gestión Documental CADIDO")
        lbl_titulo.setObjectName("tituloApp")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        layout_principal.addWidget(lbl_titulo)

        layout_principal.addLayout(self._create_buttons_panel())
        layout_principal.addWidget(self._create_status_panel())
        
        lbl_subtitulo = QLabel("📑 Documentos Procesados")
        lbl_subtitulo.setObjectName("subtituloTabla")
        layout_principal.addWidget(lbl_subtitulo)

        self.tabla = QTableWidget(0, 4)
        self._configure_table()
        layout_principal.addWidget(self.tabla)

        return widget

    def _create_buttons_panel(self) -> QHBoxLayout:
        layout_botones = QHBoxLayout()
        layout_botones.setSpacing(15)

        self.btn_seleccionar = QPushButton("📄 1. Cargar PDF")
        
        self.btn_clasificar = QPushButton("🧠 2. Clasificar con IA")
        self.btn_clasificar.setEnabled(False)
        self.btn_clasificar.setToolTip("Disponible tras cargar un documento")

        self.btn_archivar = QPushButton("📦 3. Archivar en Red")
        self.btn_archivar.setEnabled(False)
        self.btn_archivar.setStyleSheet("background-color: #4B5563;")

        self.btn_consultar = QPushButton("🔄 Actualizar Tabla")
        self.btn_consultar.setObjectName("btnSecundario")

        layout_botones.addWidget(self.btn_seleccionar)
        layout_botones.addWidget(self.btn_clasificar)
        layout_botones.addWidget(self.btn_archivar)
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_consultar)
        return layout_botones

    def _create_status_panel(self) -> QFrame:
        self.panel_estado = QFrame()
        self.panel_estado.setObjectName("panelEstado")
        self.panel_estado.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        layout_estado = QVBoxLayout(self.panel_estado)
        layout_estado.setContentsMargins(25, 20, 25, 20)
        layout_estado.setSpacing(12)

        self.lbl_estado = QLabel("🟢 Sistema listo. Esperando documento...")
        self.lbl_estado.setObjectName("estadoActivo")
        self.lbl_estado.setFont(QFont("Segoe UI", 12, QFont.Bold))

        self.lbl_resultado = QLabel("Utilice el botón 'Cargar PDF' para iniciar el análisis de un nuevo documento.")
        self.lbl_resultado.setWordWrap(True)
        self.lbl_resultado.setFont(QFont("Segoe UI", 11))
        self.lbl_resultado.setTextFormat(Qt.RichText)

        layout_estado.addWidget(self.lbl_estado)
        layout_estado.addWidget(self.lbl_resultado)
        return self.panel_estado

    def _configure_table(self) -> None:
        self.tabla.setHorizontalHeaderLabels(["Folio", "Remitente", "Asunto", "Fase Actual"])
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSortingEnabled(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)

    def _connect_signals(self) -> None:
        self.btn_seleccionar.clicked.connect(self.view_model.seleccionar_archivo)
        self.btn_clasificar.clicked.connect(self.view_model.clasificar_documento)
        self.btn_archivar.clicked.connect(self.ejecutar_archivado)
        self.btn_consultar.clicked.connect(self.cargar_datos_tabla)

        self.view_model.estado_cambiado.connect(self.actualizar_estado)
        self.view_model.analisis_completado.connect(self.mostrar_resultado)
        self.view_model.fase_cambiada.connect(self.habilitar_botones)
        self.view_model.url_pdf_cambiada.connect(self.web_view.load)

    def _initialize_data(self) -> None:
        self.cargar_datos_tabla()

    @Slot()
    def ejecutar_archivado(self) -> None:
        fila_actual = self.tabla.currentRow()
        if fila_actual < 0:
            self.actualizar_estado("Por favor, selecciona un documento de la tabla primero.")
            return

        folio = self.tabla.item(fila_actual, 0).text()
        self.view_model.archivar_documento(folio)

    @Slot(str)
    def actualizar_estado(self, mensaje: str) -> None:
        self.lbl_estado.setText(f"ℹ️ {mensaje}")
        if "¡Éxito!" in mensaje:
            self.cargar_datos_tabla()

    @Slot(FaseCicloVida)
    def habilitar_botones(self, fase: Optional[FaseCicloVida]) -> None:
        if fase is None:
            return
            
        config = self.FASE_CONFIG.get(fase, ButtonState(False, "", False))
        
        self.btn_clasificar.setEnabled(config.clasificar_enabled)
        self.btn_clasificar.setToolTip(config.clasificar_tooltip)
        self.btn_archivar.setEnabled(config.archivar_enabled)

    @Slot(object)
    def mostrar_resultado(self, datos: AnalisisDocumento) -> None:
        html = RESULTADO_TEMPLATE.safe_substitute(
            remitente=datos.remitente,
            asunto=datos.asunto,
            estatus=datos.estatus_sugerido
        )
        self.lbl_resultado.setText(html)

    @Slot()
    def cargar_datos_tabla(self) -> None:
        self.loader = DocumentLoader(page=1, page_size=100)
        self.loader.documents_loaded.connect(self._populate_table)
        self.loader.error_occurred.connect(lambda e: self.actualizar_estado(f"Error en BD: revise el log. {e}"))
        self.loader.start()

    def _populate_table(self, documentos: list) -> None:
        self.tabla.setUpdatesEnabled(False)
        self.tabla.setRowCount(len(documentos))

        for row, doc_tuple in enumerate(documentos):
            folio_oficial, remitente, asunto, fase_ciclo_vida = doc_tuple
            item_folio = self._create_table_item(folio_oficial or "Sin Folio", Qt.AlignCenter)
            item_remitente = self._create_table_item(remitente or "Desconocido")
            item_asunto = self._create_table_item(asunto or "Sin Asunto")
            
            fase_texto = fase_ciclo_vida.value if fase_ciclo_vida else "N/A"
            item_fase = self._create_table_item(fase_texto, Qt.AlignCenter)
            self._configurar_color_fase(item_fase, fase_texto)

            self.tabla.setItem(row, 0, item_folio)
            self.tabla.setItem(row, 1, item_remitente)
            self.tabla.setItem(row, 2, item_asunto)
            self.tabla.setItem(row, 3, item_fase)

        self.tabla.setUpdatesEnabled(True)

    def _configurar_color_fase(self, item: QTableWidgetItem, fase: str) -> None:
        if fase == "Clasificado":
            item.setForeground(QColor("#059669"))
            item.setFont(QFont("Segoe UI", -1, QFont.Bold))
        else:
            item.setForeground(QColor("#6B7280"))

    def _create_table_item(self, text: str, alignment: int = Qt.AlignLeft | Qt.AlignVCenter) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(alignment)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item


def main():
    try:
        settings = Settings()
    except Exception as e:
        logger.error(f"Error de configuración: {e}")
        sys.exit(1)

    crear_base_datos_y_tablas()

    # Inyección de dependencias con configuración tipada
    storage = NetworkStorageManager(settings.network_base_path)
    analyzer = DocumentAnalyzerService(api_key=settings.gemini_api_key)
    ocr = OcrProcessor()
    view_model = DocumentoViewModel(analyzer, ocr, storage)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    stylesheet = AppStyles.load_main_window_style(Path("styles.qss"))
    app.setStyleSheet(stylesheet)
    
    window = MainWindow(view_model)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()