# src/infrastructure/document_analyzer.py
from google import genai
import json
import re
import logging

logger = logging.getLogger(__name__)

class DocumentAnalyzerService:
    def __init__(self, api_key: str):
        # Usamos el nuevo SDK de google-genai
        self.client = genai.Client(api_key=api_key)

    def construir_prompt_sistema(self) -> str:
        return """
        Eres un asistente experto en análisis documental según las normas CADIDO.
        Analiza el texto proporcionado y extrae la siguiente información en formato JSON estricto:
        {
            "folio": "string o null",
            "remitente": "string (requerido)",
            "asunto": "string (requerido)",
            "es_urgente": boolean,
            "estatus_sugerido": "RESPUESTA" | "GESTION" | "AVISO" | "ARCHIVAR"
        }
        Responde ÚNICAMENTE con el objeto JSON.
        """

    def analizar_documento(self, texto_documento: str) -> dict:
        prompt = self.construir_prompt_sistema()
        
        try:
            # La nueva sintaxis es más limpia y permite gemini-2.0-flash
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"{prompt}\n\nTexto del documento: {texto_documento}"
            )
            
            return self._extraer_json(response.text)
            
        except Exception as e:
            logger.error("Error al comunicar con Gemini: %s", e, exc_info=True)
            raise RuntimeError("Fallo al analizar el documento con IA.") from e

    def _extraer_json(self, respuesta_texto: str) -> dict:
        # Intenta parsear directamente
        try:
            return json.loads(respuesta_texto)
        except json.JSONDecodeError:
            pass
        
        # Busca un bloque de código JSON (con o sin etiqueta)
        patron = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(patron, respuesta_texto)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Si nada funciona, lanza una excepción clara
        raise ValueError("No se pudo extraer JSON válido de la respuesta de la IA")