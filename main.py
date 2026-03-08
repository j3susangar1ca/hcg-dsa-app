# main.py
import sys
import os
from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from src.infrastructure.database import crear_base_datos_y_tablas
from src.infrastructure.document_analyzer import DocumentAnalyzerService
from src.infrastructure.ocr_processor import OcrProcessor
from src.presentation.documento_viewmodel import DocumentoViewModel

class MainWindow(QMainWindow):
    def __init__(self, view_model: DocumentoViewModel):
        super().__init__()
        self.setWindowTitle("CADIDO - Python Edition")
        self.resize(600, 400)
        self.view_model = view_model

        # Configurar UI
        layout = QVBoxLayout()
        
        self.lbl_estado = QLabel("Sistema listo. Fase: Nacimiento")
        self.lbl_estado.setStyleSheet("color: blue; font-weight: bold;")
        
        self.btn_seleccionar = QPushButton("1. Seleccionar Archivo PDF")
        self.btn_clasificar = QPushButton("2. Clasificar Documento (Gemini)")
        self.btn_clasificar.setEnabled(False) # Se activa al cargar un PDF
        
        self.lbl_resultado = QLabel("")
        self.lbl_resultado.setStyleSheet("background-color: #f0f0f0; padding: 10px;")

        layout.addWidget(self.lbl_estado)
        layout.addWidget(self.btn_seleccionar)
        layout.addWidget(self.btn_clasificar)
        layout.addWidget(self.lbl_resultado)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Conectar Botones a los Comandos del ViewModel
        self.btn_seleccionar.clicked.connect(self.view_model.seleccionar_archivo)
        self.btn_clasificar.clicked.connect(self.view_model.clasificar_documento)

        # Conectar Señales del ViewModel a la Vista
        self.view_model.estado_cambiado.connect(self.lbl_estado.setText)
        self.view_model.analisis_completado.connect(self.mostrar_resultado)
        self.view_model.fase_cambiada.connect(self.habilitar_botones)

    def habilitar_botones(self, fase):
        # Si pasó de nacimiento a ingresado, habilitar botón de IA
        if fase.value == "Ingresado":
            self.btn_clasificar.setEnabled(True)

    def mostrar_resultado(self, datos: dict):
        texto = f"<b>Remitente:</b> {datos.get('remitente')}<br>" \
                f"<b>Asunto:</b> {datos.get('asunto')}<br>" \
                f"<b>Acción sugerida:</b> {datos.get('estatus_sugerido')}"
        self.lbl_resultado.setText(texto)

if __name__ == "__main__":
    crear_base_datos_y_tablas()
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Inyectar dependencias
    api_key = os.getenv("GEMINI_API_KEY")
    analyzer = DocumentAnalyzerService(api_key)
    ocr = OcrProcessor()
    
    view_model = DocumentoViewModel(analyzer, ocr)
    
    app = QApplication(sys.argv)
    window = MainWindow(view_model)
    window.show()
    sys.exit(app.exec())