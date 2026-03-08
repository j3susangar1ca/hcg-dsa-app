import random
import os
import logging
from pathlib import Path
from urllib.request import pathname2url
from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QFileDialog
from src.domain.enums import FaseCicloVida
from src.domain.schemas import AnalisisDocumento
from src.infrastructure.document_analyzer import DocumentAnalyzerService
from src.infrastructure.ocr_processor import OcrProcessor
from src.infrastructure import crypto_sealer
from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from src.infrastructure.database import engine
from src.domain.entities import DocumentoPrincipal, BitacoraTrazabilidad
from src.infrastructure.network_storage import NetworkStorageManager
from typing import TypedDict

logger = logging.getLogger(__name__)

class PdfProcessingError(Exception):
    pass

class DatabaseError(Exception):
    pass

class OcrWorker(QThread):
    resultado = Signal(str)
    error = Signal(str)
    
    def __init__(self, ocr_processor: OcrProcessor, ruta: str):
        super().__init__()
        self.ocr_processor = ocr_processor
        self.ruta = ruta
        
    def run(self):
        try:
            texto = self.ocr_processor.extraer_texto(self.ruta)
            self.resultado.emit(texto)
        except Exception as e:
            self.error.emit(str(e))

class ClasificadorWorker(QThread):
    resultado = Signal(object) # AnalisisDocumento
    error = Signal(str)
    
    def __init__(self, analyzer: DocumentAnalyzerService, texto_ocr: str):
        super().__init__()
        self.analyzer = analyzer
        self.texto_ocr = texto_ocr
    
    def run(self):
        try:
            resultado_ia = self.analyzer.analizar_documento(self.texto_ocr)
            self.resultado.emit(resultado_ia)
        except Exception as e:
            self.error.emit(str(e))

class ArchivadorWorker(QThread):
    resultado = Signal(str)
    error = Signal(str)
    
    def __init__(self, storage: NetworkStorageManager, doc: DocumentoPrincipal):
        super().__init__()
        self.storage = storage
        self.doc = doc
        
    def run(self):
        try:
            nueva_ruta = self.storage.mover_a_archivo_final(
                self.doc.ruta_red_actual, "CORRESPONDENCIA_GENERAL", self.doc.folio_oficial
            )
            self.resultado.emit(nueva_ruta)
        except Exception as e:
            self.error.emit(str(e))

class DocumentoViewModel(QObject):
    fase_cambiada = Signal(FaseCicloVida)
    estado_cambiado = Signal(str)
    analisis_completado = Signal(object) # AnalisisDocumento
    archivo_seleccionado = Signal(str)
    archivo_movido = Signal(str)
    url_pdf_cambiada = Signal(str)

    def __init__(self, analyzer_service: DocumentAnalyzerService, ocr_processor: OcrProcessor, storage: NetworkStorageManager):
        super().__init__()
        self._analyzer_service = analyzer_service
        self._ocr_processor = ocr_processor
        self._storage = storage
        self.fase_actual = FaseCicloVida.NACIMIENTO
        self.texto_ocr = ""
        self.ruta_archivo = ""

    @Slot()
    def seleccionar_archivo(self) -> None:
        file_dialog = QFileDialog()
        ruta, _ = file_dialog.getOpenFileName(None, "Seleccionar PDF", "", "Archivos PDF (*.pdf)")
        
        if ruta:
            try:
                self.ruta_archivo = ruta
                self.archivo_seleccionado.emit(ruta)
                
                # Conversión robusta a URL de archivo (Oportunidad 1)
                ruta_path = Path(ruta)
                url = f"file://{pathname2url(str(ruta_path))}"
                self.url_pdf_cambiada.emit(url)
                
                self.estado_cambiado.emit(f"Archivo cargado: {ruta_path.name}. Extrayendo texto (OCR)...")
                
                self.ocr_worker = OcrWorker(self._ocr_processor, ruta)
                self.ocr_worker.resultado.connect(self._on_ocr_completado)
                self.ocr_worker.error.connect(lambda e: self.estado_cambiado.emit(f"Error al leer PDF: {e}"))
                self.ocr_worker.start()
            except Exception as e:
                self.estado_cambiado.emit(f"Error inesperado cargando PDF: {e}")
                raise PdfProcessingError(f"Fallo al seleccionar documento {ruta}") from e

    def _on_ocr_completado(self, texto: str) -> None:
        self.texto_ocr = texto
        self.estado_cambiado.emit("Texto extraído correctamente. Listo para clasificar.")
        self.fase_actual = FaseCicloVida.INGRESADO
        self.fase_cambiada.emit(self.fase_actual)

    @Slot()
    def clasificar_documento(self) -> None:
        if not self.texto_ocr:
            self.estado_cambiado.emit("Error: Primero debes seleccionar un PDF válido.")
            return

        self.estado_cambiado.emit("Clasificando documento con IA...")
        
        self.cls_worker = ClasificadorWorker(self._analyzer_service, self.texto_ocr)
        self.cls_worker.resultado.connect(self._on_clasificacion_completada)
        self.cls_worker.error.connect(lambda e: self.estado_cambiado.emit(f"Error en clasificación: {e}"))
        self.cls_worker.start()

    def _on_clasificacion_completada(self, resultado_ia: AnalisisDocumento) -> None:
        self.fase_actual = FaseCicloVida.CLASIFICADO
        self.fase_cambiada.emit(self.fase_actual)
        self.analisis_completado.emit(resultado_ia)
        self.guardar_clasificacion(resultado_ia)

    @Slot(object)
    def guardar_clasificacion(self, datos_ia: AnalisisDocumento) -> None:
        session: Session | None = None
        try:
            with Session(engine) as session:
                nuevo_doc = DocumentoPrincipal(
                    folio_oficial=datos_ia.folio or "SIN_FOLIO",
                    remitente=datos_ia.remitente,
                    asunto=datos_ia.asunto,
                    ruta_red_actual=self.ruta_archivo,
                    hash_criptografico=crypto_sealer.generar_hash_sha256(self.ruta_archivo),
                    fase_ciclo_vida=FaseCicloVida.CLASIFICADO
                )
                
                session.add(nuevo_doc)

                bitacora = BitacoraTrazabilidad(
                    documento_id=nuevo_doc.id,
                    fase_anterior=FaseCicloVida.NACIMIENTO.value,
                    fase_nueva=FaseCicloVida.CLASIFICADO.value,
                    descripcion_evento=f"Documento clasificado por IA. Folio: {nuevo_doc.folio_oficial}"
                )
                session.add(bitacora)
                
                session.commit()
                self.estado_cambiado.emit(f"¡Éxito! Documento guardado en BD con ID: {nuevo_doc.id}")
        except SQLAlchemyError as e:
            if session:
                session.rollback()
            logger.error("Error al persistir en BD: %s", e, exc_info=True)
            self.estado_cambiado.emit(f"Error al persistir en BD.")
            raise DatabaseError("Fallo al guardar clasificación") from e

    @Slot(str)
    def archivar_documento(self, folio: str) -> None:
        try:
            with Session(engine) as session:
                statement = select(DocumentoPrincipal).where(DocumentoPrincipal.folio_oficial == folio)
                doc = session.exec(statement).first()
                if not doc:
                    self.estado_cambiado.emit("Error: No se encontró el registro en la BD.")
                    return
                
                self.estado_cambiado.emit(f"Moviendo archivo a red...")
                self.arch_worker = ArchivadorWorker(self._storage, doc)
                
                def on_archivo_movido(nueva_ruta):
                    session2 = None
                    try:
                        with Session(engine) as session2:
                            doc2 = session2.exec(select(DocumentoPrincipal).where(DocumentoPrincipal.id == doc.id)).first()
                            if doc2:
                                fase_anterior = doc2.fase_ciclo_vida
                                doc2.fase_ciclo_vida = FaseCicloVida.ARCHIVADO
                                doc2.ruta_red_actual = nueva_ruta
                                
                                bitacora = BitacoraTrazabilidad(
                                    documento_id=doc2.id,
                                    fase_anterior=fase_anterior.value,
                                    fase_nueva=FaseCicloVida.ARCHIVADO.value,
                                    descripcion_evento=f"Archivo movido físicamente a red: {nueva_ruta}"
                                )
                                session2.add(doc2)
                                session2.add(bitacora)
                                session2.commit()
                                
                                self.estado_cambiado.emit(f"¡Éxito! Archivo movido a red: {nueva_ruta}")
                                self.fase_cambiada.emit(doc2.fase_ciclo_vida)
                                self.archivo_movido.emit(nueva_ruta)
                    except SQLAlchemyError as e:
                        if session2:
                            session2.rollback()
                        raise DatabaseError("Fallo actualizando la base de datos tras archivo") from e
                            
                self.arch_worker.resultado.connect(on_archivo_movido)
                self.arch_worker.error.connect(lambda e: self.estado_cambiado.emit(f"Error al archivar en red: {e}"))
                self.arch_worker.start()
                
        except Exception as e:
            logger.error("Error al preparar archivo para red: %s", e, exc_info=True)
            self.estado_cambiado.emit(f"Error al archivar.")