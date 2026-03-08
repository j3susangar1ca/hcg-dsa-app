from google import genai
import json
import re
import logging
from enum import Enum, auto
from pydantic import ValidationError
from src.domain.schemas import AnalisisDocumento
from src.infrastructure.config import Settings

logger = logging.getLogger(__name__)

class AnalysisMode(Enum):
    PRODUCTION = auto()
    SIMULATION = auto()

class DocumentAnalyzerService:
    def __init__(self, api_key: str | None = None, mode: AnalysisMode = AnalysisMode.PRODUCTION):
        self.mode = mode
        if mode == AnalysisMode.PRODUCTION:
            self.client = genai.Client(api_key=api_key or Settings().gemini_api_key)

    def _construir_prompt_sistema(self) -> str:
        return """
        Eres un asistente experto en análisis documental según las normas CADIDO.
        Analiza el texto proporcionado y extrae la siguiente información en formato JSON estricto:
        {
            "folio": "string o null",
            "remitente": "string (requerido)",
            "asunto": "string (requerido)",
            "es_urgente": boolean,
            "estatus_sugerido": "Respuesta" | "Gestion" | "Aviso" | "Archivar"
        }
        Responde ÚNICAMENTE con el objeto JSON.
        """

    def analizar_documento(self, texto_documento: str) -> AnalisisDocumento:
        if self.mode == AnalysisMode.SIMULATION:
            return AnalisisDocumento(
                folio="SIM-123",
                remitente="Remitente Simulado",
                asunto="Asunto en Modo Simulación",
                es_urgente=False,
                estatus_sugerido="Gestion"
            )

        prompt = self._construir_prompt_sistema()
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"{prompt}\n\nTexto del documento: {texto_documento}"
            )
            raw_dict = self._extraer_json(response.text)
            return AnalisisDocumento.model_validate(raw_dict)
            
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error("Error al validar respuesta de IA: %s", e)
            raise ValueError(f"Respuesta inválida de IA: {e}") from e
        except Exception as e:
            logger.error("Error general con Gemini: %s", e, exc_info=True)
            raise RuntimeError("Fallo al analizar el documento con IA.") from e

    def _extraer_json(self, respuesta_texto: str) -> dict:
        try:
            return json.loads(respuesta_texto)
        except json.JSONDecodeError:
            pass
            
        patron = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(patron, respuesta_texto)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
                
        raise ValueError("No se pudo extraer JSON válido de la respuesta")