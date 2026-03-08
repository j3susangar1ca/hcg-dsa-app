# src/infrastructure/document_analyzer.py
from google import genai
import json

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
            
            # Limpiamos posibles formatos de Markdown
            texto_json = response.text.replace('```json\n', '').replace('\n```', '').strip()
            
            return json.loads(texto_json)
            
        except Exception as e:
            print(f"Error al comunicar con Gemini: {e}")
            raise RuntimeError("Fallo al analizar el documento con IA.") from e