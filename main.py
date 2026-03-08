# main.py
import sys
import os
from dotenv import load_dotenv
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QPushButton, QLabel, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QFrame)
from PySide6.QtCore import Qt

from src.infrastructure.database import crear_base_datos_y_tablas
from src.infrastructure.document_analyzer import DocumentAnalyzerService
from src.infrastructure.ocr_processor import OcrProcessor
from src.presentation.documento_viewmodel import DocumentoViewModel

# --- HOJA DE ESTILOS MODERNOS (QSS) ---
ESTILO_MODERNO = """
QMainWindow {
    background-color: #F3F4F6; /* Fondo gris claro */
}

QLabel {
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    color: #1F2937;
    font-size: 14px;
}

/* Título principal */
QLabel#tituloApp {
    font-size: 24px;
    font-weight: bold;
    color: #111827;
    margin-bottom: 10px;
}

/* Panel de estado */
QFrame#panelEstado {
    background-color: #FFFFFF;
    border-radius: 8px;
    border: 1px solid #E5E7EB;
}

/* Botones principales */
QPushButton {
    background-color: #2563EB; /* Azul corporativo */
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: bold;
    font-size: 14px;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QPushButton:pressed {
    background-color: #1E40AF;
}

QPushButton:disabled {
    background-color: #9CA3AF;
    color: #F3F4F6;
}

/* Botón secundario (Consultar) */
QPushButton#btnSecundario {
    background-color: #10B981; /* Verde esmeralda */
}

QPushButton#btnSecundario:hover {
    background-color: #059669;
}

/* Tabla de datos */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    gridline-color: #F3F4F6;
    selection-background-color: #DBEAFE;
    selection-color: #1E3A8A;
    font-size: 13px;
}

QHeaderView::section {
    background-color: #F9FAFB;
    color: #4B5563;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #E5E7EB;
    font-weight: bold;
    font-size: 13px;
}
"""

class MainWindow(QMainWindow):
    def __init__(self, view_model: DocumentoViewModel):
        super().__init__()
        self.setWindowTitle("CADIDO - Gestión Documental Inteligente")
        self.resize(900, 650) # Ventana más grande para que respire el diseño
        self.view_model = view_model

        # Layout Principal
        layout_principal = QVBoxLayout()
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(15)

        # 1. Título
        lbl_titulo = QLabel("Sistema de Gestión Documental CADIDO")
        lbl_titulo.setObjectName("tituloApp")
        layout_principal.addWidget(lbl_titulo)

        # 2. Panel de Controles (Botones alineados horizontalmente)
        layout_botones = QHBoxLayout()
        
        self.btn_seleccionar = QPushButton("📄 1. Cargar PDF")
        self.btn_clasificar = QPushButton("🧠 2. Clasificar con IA")
        self.btn_clasificar.setEnabled(False)
        
        self.btn_consultar = QPushButton("🔄 Actualizar Tabla")
        self.btn_consultar.setObjectName("btnSecundario") # Aplicamos el estilo verde
        
        layout_botones.addWidget(self.btn_seleccionar)
        layout_botones.addWidget(self.btn_clasificar)
        layout_botones.addStretch() # Empuja los botones a la izquierda
        layout_botones.addWidget(self.btn_consultar)
        
        layout_principal.addLayout(layout_botones)

        # 3. Panel de Estado y Resultados
        self.panel_estado = QFrame()
        self.panel_estado.setObjectName("panelEstado")
        layout_estado = QVBoxLayout(self.panel_estado)
        layout_estado.setContentsMargins(15, 15, 15, 15)
        
        self.lbl_estado = QLabel("🟢 Sistema listo. Esperando documento...")
        self.lbl_resultado = QLabel("Aquí aparecerán los resultados de la extracción de la IA.")
        self.lbl_resultado.setWordWrap(True)
        
        layout_estado.addWidget(self.lbl_estado)
        layout_estado.addWidget(self.lbl_resultado)
        
        layout_principal.addWidget(self.panel_estado)

        # 4. Tabla de Base de Datos
        lbl_subtitulo = QLabel("Documentos Procesados:")
        lbl_subtitulo.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout_principal.addWidget(lbl_subtitulo)

        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Folio", "Remitente", "Asunto", "Fase Actual"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setAlternatingRowColors(True) # Filas de colores alternos para legibilidad
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers) # Solo lectura
        layout_principal.addWidget(self.tabla)

        # Contenedor central
        container = QWidget()
        container.setLayout(layout_principal)
        self.setCentralWidget(container)

        # Conexiones (Señales y Slots)
        self.btn_seleccionar.clicked.connect(self.view_model.seleccionar_archivo)
        self.btn_clasificar.clicked.connect(self.view_model.clasificar_documento)
        self.btn_consultar.clicked.connect(self.cargar_datos_tabla)

        self.view_model.estado_cambiado.connect(self.actualizar_estado)
        self.view_model.analisis_completado.connect(self.mostrar_resultado)
        self.view_model.fase_cambiada.connect(self.habilitar_botones)

        # Cargar tabla al iniciar
        self.cargar_datos_tabla()

    # --- Métodos de la UI ---
    def actualizar_estado(self, mensaje):
        self.lbl_estado.setText(f"ℹ️ {mensaje}")
        if "¡Éxito!" in mensaje:
            self.cargar_datos_tabla()

    def habilitar_botones(self, fase):
        if fase.value == "Ingresado":
            self.btn_clasificar.setEnabled(True)
        elif fase.value == "Clasificado":
            self.btn_clasificar.setEnabled(False)

    def mostrar_resultado(self, datos: dict):
        texto = f"<b>🏢 Remitente:</b> {datos.get('remitente')}<br><br>" \
                f"<b>📝 Asunto:</b> {datos.get('asunto')}<br><br>" \
                f"<b>🎯 Acción sugerida:</b> <span style='color: #2563EB; font-weight:bold;'>{datos.get('estatus_sugerido')}</span>"
        self.lbl_resultado.setText(texto)

    def cargar_datos_tabla(self):
        from sqlmodel import Session, select
        from src.infrastructure.database import engine
        from src.domain.entities import DocumentoPrincipal

        with Session(engine) as session:
            # Nota: Cambié fecha_creacion.desc() por id.desc() temporalmente 
            # ya que fecha_creacion fue removido de la entidad en un paso anterior.
            statement = select(DocumentoPrincipal).order_by(DocumentoPrincipal.id.desc())
            documentos = session.exec(statement).all()
            
            self.tabla.setRowCount(0)
            for row, doc in enumerate(documentos):
                self.tabla.insertRow(row)
                self.tabla.setItem(row, 0, QTableWidgetItem(doc.folio_oficial))
                self.tabla.setItem(row, 1, QTableWidgetItem(doc.remitente))
                self.tabla.setItem(row, 2, QTableWidgetItem(doc.asunto))
                
                # Le damos un color al item dependiendo de la fase
                item_fase = QTableWidgetItem(doc.fase_ciclo_vida.value)
                item_fase.setForeground(Qt.blue if doc.fase_ciclo_vida.value == "Clasificado" else Qt.black)
                self.tabla.setItem(row, 3, item_fase)

if __name__ == "__main__":
    load_dotenv()
    crear_base_datos_y_tablas()
    
    api_key = os.getenv("GEMINI_API_KEY") 
    analyzer = DocumentAnalyzerService(api_key)
    ocr = OcrProcessor()
    
    view_model = DocumentoViewModel(analyzer, ocr)
    
    app = QApplication(sys.argv)
    
    # ¡AQUÍ APLICAMOS LA MAGIA DEL DISEÑO!
    app.setStyleSheet(ESTILO_MODERNO)
    
    window = MainWindow(view_model)
    window.show()
    sys.exit(app.exec())