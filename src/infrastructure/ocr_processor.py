# src/infrastructure/ocr_processor.py

class OcrProcessor:
    def extraer_texto(self, ruta_archivo: str) -> str:
        """
        Simula la extracción de texto de un archivo PDF.
        En una implementación real, aquí se usaría PyMuPDF, pdfplumber o similares.
        """
        print(f"Extrayendo texto de: {ruta_archivo}")
        # Retornamos un texto de ejemplo para que la IA tenga algo que procesar
        return "Solicito permiso de vacaciones para el 15 de marzo. Atte: Juan Pérez."
