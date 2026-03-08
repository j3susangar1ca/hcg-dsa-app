from pydantic import BaseModel, Field
from typing import Literal

class AnalisisDocumento(BaseModel):
    folio: str | None = Field(None, max_length=50)
    remitente: str = Field(..., min_length=1, max_length=200)
    asunto: str = Field(..., min_length=1, max_length=500)
    es_urgente: bool = False
    estatus_sugerido: Literal["Respuesta", "Gestion", "Aviso", "Archivar"]
    
    class Config:
        str_strip_whitespace = True
