# src/infrastructure/ocr_processor.py
import os
import fitz  # PyMuPDF

class OcrProcessor:
    """
    Procesador real para extraer texto de archivos PDF utilizando PyMuPDF.
    """
    
    def extraer_texto(self, ruta_archivo: str) -> str:
        """
        Abre un PDF y extrae todo su texto página por página.
        """
        if not os.path.exists(ruta_archivo):
            raise FileNotFoundError(f"El archivo PDF no existe en la ruta: {ruta_archivo}")
            
        texto_completo = ""
        
        try:
            # Abrir el documento de forma segura
            with fitz.open(ruta_archivo) as doc:
                for pagina in doc:
                    # Extraer texto preservando saltos de línea básicos
                    texto_completo += pagina.get_text("text") + "\n\n"
                    
        except Exception as e:
            raise RuntimeError(f"Fallo al intentar leer el documento PDF: {str(e)}")
            
        texto_limpio = texto_completo.strip()
        
        # Validación en caso de que sea un PDF escaneado (sin texto digital)
        if not texto_limpio:
            raise ValueError("El PDF parece ser una imagen escaneada. No se encontró texto digital para extraer.")
            
        return texto_limpio

    def puede_procesar(self, ruta_archivo: str) -> bool:
        """Verifica si la extensión corresponde a un archivo procesable."""
        return ruta_archivo.lower().endswith(".pdf")
