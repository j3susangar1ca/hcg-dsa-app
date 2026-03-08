# src/presentation/documento_viewmodel.py
import random
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog
from src.domain.enums import FaseCicloVida
from src.infrastructure.document_analyzer import DocumentAnalyzerService
from src.infrastructure.ocr_processor import OcrProcessor # Importamos el OCR
from src.infrastructure.crypto_sealer import CryptoSealer # Importar
from sqlmodel import Session
from src.infrastructure.database import engine
from src.domain.entities import DocumentoPrincipal, BitacoraTrazabilidad

class DocumentoViewModel(QObject):
    fase_cambiada = Signal(FaseCicloVida)
    estado_cambiado = Signal(str)
    analisis_completado = Signal(dict)
    archivo_seleccionado = Signal(str)

    def __init__(self, analyzer_service: DocumentAnalyzerService, ocr_processor: OcrProcessor):
        super().__init__()
        self._analyzer_service = analyzer_service
        self._ocr_processor = ocr_processor
        self.fase_actual = FaseCicloVida.NACIMIENTO
        self.texto_ocr = ""
        self.ruta_archivo = ""

    @Slot()
    def seleccionar_archivo(self):
        file_dialog = QFileDialog()
        ruta, _ = file_dialog.getOpenFileName(None, "Seleccionar PDF", "", "Archivos PDF (*.pdf)")
        
        if ruta:
            self.ruta_archivo = ruta
            self.archivo_seleccionado.emit(ruta)
            self.estado_cambiado.emit(f"Archivo cargado: {ruta}. Listo para extraer texto.")
            
            # Extraemos el texto inmediatamente
            try:
                self.texto_ocr = self._ocr_processor.extraer_texto(ruta)
                self.estado_cambiado.emit("Texto extraído correctamente. Listo para clasificar.")
                self.fase_actual = FaseCicloVida.INGRESADO
                self.fase_cambiada.emit(self.fase_actual)
            except Exception as e:
                self.estado_cambiado.emit(f"Error al leer PDF: {str(e)}")

    @Slot()
    def clasificar_documento(self):
        if not self.texto_ocr:
            self.estado_cambiado.emit("Error: Primero debes seleccionar un PDF válido.")
            return

        self.estado_cambiado.emit("Clasificando documento con Gemini IA...")
        
        try:
            # Intentamos llamar a la API real
            resultado_ia = self._analyzer_service.analizar_documento(self.texto_ocr)
        except Exception as e:
            # PLAN B: Si Google da error 429, usamos datos simulados para no bloquear el desarrollo
            print(f"Usando IA Simulada debido a: {e}")
            self.estado_cambiado.emit("Advertencia: Se usó IA simulada (Límite de API).")
            
            # GENERAMOS UN FOLIO ÚNICO PARA QUE NO FALLE LA BASE DE DATOS
            folio_random = f"FOL-SIM-{random.randint(1000, 9999)}"
            
            resultado_ia = {
                "folio": folio_random,
                "remitente": "Remitente Extraído (Simulado)",
                "asunto": "Asunto detectado (Simulado)",
                "es_urgente": False,
                "estatus_sugerido": "GESTION"
            }
            
        # Cambiamos de fase
        self.fase_actual = FaseCicloVida.CLASIFICADO
        self.fase_cambiada.emit(self.fase_actual)
        self.analisis_completado.emit(resultado_ia)
        
        # Guardar en BD
        self.guardar_clasificacion(resultado_ia)

    @Slot(dict)
    def guardar_clasificacion(self, datos_ia):
        """Equivalente a la lógica de UnitOfWork.SaveChangesAsync()"""
        try:
            with Session(engine) as session:
                # 1. Crear el objeto Documento (Traducción del DTO)
                nuevo_doc = DocumentoPrincipal(
                    folio_oficial=datos_ia.get("folio") or "SIN_FOLIO",
                    remitente=datos_ia.get("remitente"),
                    asunto=datos_ia.get("asunto"),
                    ruta_red_actual=self.ruta_archivo,
                    hash_criptografico=CryptoSealer.generar_hash_sha256(self.ruta_archivo),
                    is_urgente=datos_ia.get("es_urgente", False),
                    fase_ciclo_vida=FaseCicloVida.CLASIFICADO
                )
                
                session.add(nuevo_doc)
                session.flush() # Para obtener el ID del documento antes del commit

                # 2. Registrar en Bitácora (Equivalente a RegistrarEventoBitacoraAsync)
                bitacora = BitacoraTrazabilidad(
                    documento_id=nuevo_doc.id,
                    fase_anterior=FaseCicloVida.NACIMIENTO.value,
                    fase_nueva=FaseCicloVida.CLASIFICADO.value,
                    descripcion_evento=f"Documento clasificado por IA. Folio: {nuevo_doc.folio_oficial}"
                )
                session.add(bitacora)
                
                # 3. Commit de la transacción (Atómico como en C#)
                session.commit()
                self.estado_cambiado.emit(f"¡Éxito! Documento guardado en BD con ID: {nuevo_doc.id}")
        except Exception as e:
            self.estado_cambiado.emit(f"Error al persistir en BD: {str(e)}")