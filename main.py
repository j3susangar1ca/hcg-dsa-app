# main.py
import sys
import os
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSizePolicy, QSplitter
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QColor

# Módulos internos
from sqlmodel import Session, select
from src.infrastructure.database import engine, crear_base_datos_y_tablas
from src.domain.entities import DocumentoPrincipal
from src.infrastructure.document_analyzer import DocumentAnalyzerService
from src.infrastructure.ocr_processor import OcrProcessor
from src.infrastructure.network_storage import NetworkStorageManager
from src.presentation.documento_viewmodel import DocumentoViewModel


# --- HOJA DE ESTILOS PROFESIONAL (QSS) ---
# Nota: Se han eliminado propiedades no soportadas como 'transform' y 'box-shadow' complejo
# para asegurar el renderizado correcto en todas las plataformas.
ESTILO_MODERNO = """
/* --- Ventana Principal --- */
QMainWindow {
    background-color: #F3F4F6;
}

/* --- Etiquetas Generales --- */
QLabel {
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    color: #1F2937;
    font-size: 14px;
}

/* Título principal */
QLabel#tituloApp {
    font-size: 28px;
    font-weight: bold;
    color: #111827;
    padding: 10px;
}

/* Subtítulo de sección */
QLabel#subtituloTabla {
    font-size: 16px;
    font-weight: bold;
    color: #374151;
    margin-top: 15px;
    margin-bottom: 5px;
}

/* Panel de estado */
QFrame#panelEstado {
    background-color: #FFFFFF;
    border-radius: 10px;
    border: 1px solid #E5E7EB;
    min-height: 100px;
}

/* --- Botones --- */
QPushButton {
    background-color: #2563EB;
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: bold;
    font-size: 14px;
    text-align: center;
    min-width: 160px;
    min-height: 45px;
}

QPushButton:hover {
    background-color: #1D4ED8;
    border: 1px solid #1E40AF;
}

QPushButton:pressed {
    background-color: #1E40AF;
    padding-top: 13px; /* Efecto de presión visual */
    padding-bottom: 11px;
}

QPushButton:disabled {
    background-color: #E5E7EB;
    color: #9CA3AF;
    border: none;
}

/* Botón secundario (Consultar/Actualizar) */
QPushButton#btnSecundario {
    background-color: #10B981;
}

QPushButton#btnSecundario:hover {
    background-color: #059669;
    border: 1px solid #047857;
}

QPushButton#btnSecundario:pressed {
    background-color: #047857;
}

/* --- Tabla de Datos --- */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    gridline-color: #F3F4F6;
    selection-background-color: #DBEAFE;
    selection-color: #1E3A8A;
    font-size: 13px;
    outline: none; /* Elimina el borde de selección de celda */
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #E5E7EB;
}

QTableWidget::item:selected {
    background-color: #EFF6FF;
    color: #1E40AF;
}

QHeaderView::section {
    background-color: #F9FAFB;
    color: #4B5563;
    padding: 12px 8px;
    border: none;
    border-bottom: 2px solid #E5E7EB;
    font-weight: bold;
    font-size: 13px;
    text-transform: uppercase;
}

QTableCornerButton::section {
    background-color: #F9FAFB;
    border: none;
    border-right: 1px solid #E5E7EB;
    border-bottom: 2px solid #E5E7EB;
}

/* Etiquetas de estado específicas */
QLabel#estadoActivo {
    color: #059669;
    font-weight: bold;
}

QLabel#estadoInactivo {
    color: #DC2626;
    font-weight: bold;
}
"""


class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación CADIDO - Gestión Documental Inteligente.
    
    Esta clase actúa como la Vista en el patrón MVVM, encargándose únicamente de 
    la presentación de datos y captura de eventos del usuario, delegando la lógica 
    de negocio al DocumentoViewModel.
    """

    def __init__(self, view_model: DocumentoViewModel):
        super().__init__()
        self.view_model = view_model
        
        # Configuración inicial
        self._setup_window_properties()
        self._setup_ui()
        self._connect_signals()
        self._initialize_data()

    def _setup_window_properties(self):
        """Configura las propiedades básicas de la ventana"""
        self.setWindowTitle("CADIDO - Gestión Documental Inteligente")
        self.resize(1024, 768)  # Resolución inicial más estándar
        self.setMinimumSize(900, 650)
        self.setStyleSheet(ESTILO_MODERNO)

    def _setup_ui(self):
        """Construye y configura todos los componentes de la interfaz gráfica."""
        
        # 1. Creamos el visor de PDF (Navegador ligero)
        self.web_view = QWebEngineView()
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.PluginsEnabled, True)
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.PdfViewerEnabled, True)
        self.web_view.setMinimumWidth(500)
        
        # 2. Usamos un QSplitter para dividir la pantalla
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Contenedor Izquierdo (Todo lo antiguo)
        self.widget_izquierdo = QWidget()
        layout_principal = QVBoxLayout(self.widget_izquierdo)
        layout_principal.setContentsMargins(30, 30, 30, 30)
        layout_principal.setSpacing(20)

        # 1. Encabezado
        lbl_titulo = QLabel("Sistema de Gestión Documental CADIDO")
        lbl_titulo.setObjectName("tituloApp")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        layout_principal.addWidget(lbl_titulo)

        # 2. Barra de Herramientas (Botones)
        layout_botones = QHBoxLayout()
        layout_botones.setSpacing(15)

        self.btn_seleccionar = QPushButton("📄 1. Cargar PDF")
        self.btn_clasificar = QPushButton("🧠 2. Clasificar con IA")
        self.btn_clasificar.setEnabled(False)
        self.btn_clasificar.setToolTip("Disponible tras cargar un documento")

        self.btn_archivar = QPushButton("📦 3. Archivar en Red")
        self.btn_archivar.setEnabled(False)
        self.btn_archivar.setStyleSheet("background-color: #4B5563;") # Gris oscuro profesional

        self.btn_consultar = QPushButton("🔄 Actualizar Tabla")
        self.btn_consultar.setObjectName("btnSecundario")

        # Agrupar botones de acción a la izquierda
        layout_botones.addWidget(self.btn_seleccionar)
        layout_botones.addWidget(self.btn_clasificar)
        layout_botones.addWidget(self.btn_archivar)
        layout_botones.addStretch()  # Empuja el siguiente botón a la derecha
        layout_botones.addWidget(self.btn_consultar)
        
        layout_principal.addLayout(layout_botones)

        # 3. Panel de Estado (Dashboard superior)
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
        self.lbl_resultado.setTextFormat(Qt.RichText) # Permite HTML básico

        layout_estado.addWidget(self.lbl_estado)
        layout_estado.addWidget(self.lbl_resultado)
        
        layout_principal.addWidget(self.panel_estado)

        # 4. Sección de Tabla de Datos
        lbl_subtitulo = QLabel("📑 Documentos Procesados")
        lbl_subtitulo.setObjectName("subtituloTabla")
        layout_principal.addWidget(lbl_subtitulo)

        self.tabla = QTableWidget(0, 4)
        self._configure_table()
        layout_principal.addWidget(self.tabla)

        # Ensamblaje final
        self.splitter.addWidget(self.widget_izquierdo)
        self.splitter.addWidget(self.web_view)
        
        # Configuramos proporciones iniciales del splitter
        self.splitter.setSizes([400, 600])

        self.setCentralWidget(self.splitter)

    def _configure_table(self):
        """Configura propiedades avanzadas de la tabla."""
        self.tabla.setHorizontalHeaderLabels(["Folio", "Remitente", "Asunto", "Fase Actual"])
        
        # Configuración de encabezados
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # Folio ajustado
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Remitente flexible
        header.setSectionResizeMode(2, QHeaderView.Stretch)          # Asunto flexible
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Fase ajustada
        
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSortingEnabled(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False) # Diseño más limpio, usando bordes de items

    def _connect_signals(self):
        """Vincula las señales de la UI y el ViewModel con sus respectivos slots."""
        # Señales de la UI hacia el ViewModel
        self.btn_seleccionar.clicked.connect(self.view_model.seleccionar_archivo)
        self.btn_clasificar.clicked.connect(self.view_model.clasificar_documento)
        self.btn_archivar.clicked.connect(self.ejecutar_archivado)
        self.btn_consultar.clicked.connect(self.cargar_datos_tabla)

        # Señales del ViewModel hacia la UI
        self.view_model.estado_cambiado.connect(self.actualizar_estado)
        self.view_model.analisis_completado.connect(self.mostrar_resultado)
        self.view_model.fase_cambiada.connect(self.habilitar_botones)
        
        # 3. Conectar la señal del PDF
        self.view_model.url_pdf_cambiada.connect(self.web_view.load)

    def _initialize_data(self):
        """Carga inicial de datos necesarios para la aplicación."""
        self.cargar_datos_tabla()

    @Slot()
    def ejecutar_archivado(self):
        # Obtenemos el folio de la fila seleccionada en la tabla
        fila_actual = self.tabla.currentRow()
        if fila_actual < 0:
            self.actualizar_estado("Por favor, selecciona un documento de la tabla primero.")
            return

        folio = self.tabla.item(fila_actual, 0).text()
        self.view_model.archivar_documento(folio)

    @Slot(str)
    def actualizar_estado(self, mensaje: str):
        """
        Actualiza la etiqueta de estado en la interfaz.
        
        Args:
            mensaje: Texto del estado proveniente del ViewModel.
        """
        self.lbl_estado.setText(f"ℹ️ {mensaje}")
        
        # Si el mensaje indica éxito, refrescamosos la tabla automáticamente
        if "¡Éxito!" in mensaje:
            self.cargar_datos_tabla()

    @Slot(object)
    def habilitar_botones(self, fase: Optional[Any]):
        """
        Modifica la disponibilidad de los controles según la fase actual del documento.
        
        Args:
            fase: Objeto enumerado (Enum) que representa la fase del ciclo de vida.
        """
        # Verificamos si el objeto fase tiene el atributo 'value' (seguridad)
        if not hasattr(fase, 'value'):
            return

        fase_valor = fase.value
        
        if fase_valor == "Ingresado":
            self.btn_clasificar.setEnabled(True)
            self.btn_clasificar.setToolTip("Listo para clasificar")
            self.btn_archivar.setEnabled(False)
        elif fase_valor == "Clasificado":
            self.btn_clasificar.setEnabled(False)
            self.btn_clasificar.setToolTip("El documento ya ha sido clasificado")
            self.btn_archivar.setEnabled(True)

    @Slot(dict)
    def mostrar_resultado(self, datos: Dict[str, Any]):
        """
        Renderiza los resultados del análisis de IA en el panel de estado.
        
        Args:
            datos: Diccionario con claves 'remitente', 'asunto', 'estatus_sugerido'.
        """
        html_template = (
            f"<div style='line-height: 1.6;'>"
            f"<b>🏢 Remitente:</b> {datos.get('remitente', 'No identificado')}<br><br>"
            f"<b>📝 Asunto:</b> {datos.get('asunto', 'No identificado')}<br><br>"
            f"<b>🎯 Acción sugerida:</b> "
            f"<span style='color: #2563EB; font-weight:bold; font-size: 13px;'>"
            f"{datos.get('estatus_sugerido', 'Pendiente')}</span>"
            f"</div>"
        )
        self.lbl_resultado.setText(html_template)

    @Slot()
    def cargar_datos_tabla(self):
        """
        Consulta la base de datos y pobla el QTableWidget con los registros.
        Utiliza transacción segura y optimiza la renderización bloqueando señales.
        """
        try:
            with Session(engine) as session:
                statement = select(DocumentoPrincipal).order_by(DocumentoPrincipal.id.desc())
                documentos: List[DocumentoPrincipal] = session.exec(statement).all()

                # Optimización: Bloquear repaints mientras se llena la tabla
                self.tabla.setUpdatesEnabled(False)
                self.tabla.setRowCount(len(documentos))

                for row, doc in enumerate(documentos):
                    # Crear items alineados y formateados
                    item_folio = self._create_table_item(doc.folio_oficial or "Sin Folio", Qt.AlignCenter)
                    item_remitente = self._create_table_item(doc.remitente or "Desconocido")
                    item_asunto = self._create_table_item(doc.asunto or "Sin Asunto")
                    
                    # Lógica de color para la fase
                    fase_texto = doc.fase_ciclo_vida.value if doc.fase_ciclo_vida else "N/A"
                    item_fase = self._create_table_item(fase_texto, Qt.AlignCenter)
                    
                    if fase_texto == "Clasificado":
                        item_fase.setForeground(QColor("#059669")) # Verde oscuro
                        item_fase.setFont(QFont("Segoe UI", -1, QFont.Bold))
                    else:
                        item_fase.setForeground(QColor("#6B7280")) # Gris

                    # Asignar items a la fila
                    self.tabla.setItem(row, 0, item_folio)
                    self.tabla.setItem(row, 1, item_remitente)
                    self.tabla.setItem(row, 2, item_asunto)
                    self.tabla.setItem(row, 3, item_fase)

                self.tabla.setUpdatesEnabled(True)

        except Exception as e:
            print(f"Error crítico al cargar datos: {e}")
            # Opcional: Mostrar mensaje en la barra de estado si existiera

    def _create_table_item(self, text: str, alignment: int = Qt.AlignLeft | Qt.AlignVCenter) -> QTableWidgetItem:
        """
        Factory method para crear items de tabla con formato estándar.
        
        Args:
            text: Contenido textual de la celda.
            alignment: Banderas de alineación de Qt.
            
        Returns:
            QTableWidgetItem configurado.
        """
        item = QTableWidgetItem(text)
        item.setTextAlignment(alignment)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable) # Asegurar no editable
        return item


def main():
    """Punto de entrada principal de la aplicación."""
    # Cargar variables de entorno
    load_dotenv()

    # Inicializar infraestructura
    crear_base_datos_y_tablas()

    # Validar configuración crítica
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("Error de configuración: GEMINI_API_KEY no está definida en el archivo .env")

    # Inyección de dependencias
    analyzer = DocumentAnalyzerService(api_key)
    ocr = OcrProcessor()
    storage = NetworkStorageManager()
    view_model = DocumentoViewModel(analyzer, ocr, storage)

    # Inicializar aplicación Qt
    app = QApplication(sys.argv)
    
    # Configuración global de la app (opcional, para alta DPI)
    app.setStyle("Fusion") # Fusion suele renderizar mejor los QSS modernos
    
    # Instanciar y mostrar ventana principal
    window = MainWindow(view_model)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()