# src/domain/entities.py
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship
from .enums import FaseCicloVida, EstatusAccion

class CatalogoCadido(SQLModel, table=True):
    # Definimos el nombre de la tabla explícitamente para evitar errores
    __tablename__ = "catalogocadido" 
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    seccion: str = Field(max_length=100)
    serie: str = Field(max_length=100)
    subserie: str = Field(max_length=100)
    plazo_conservacion_anios: int
    is_activo: bool = Field(default=True)

    # Relación inversa (opcional, igual que en C#)
    documentos: List["DocumentoPrincipal"] = Relationship(back_populates="catalogo")

class DocumentoPrincipal(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    folio_oficial: str = Field(index=True, unique=True, max_length=50)
    remitente: str = Field(max_length=200)
    asunto: str = Field(max_length=500)
    ruta_red_actual: str = Field(max_length=500)
    hash_criptografico: str = Field(max_length=64)
    estatus_accion: EstatusAccion = Field(default=EstatusAccion.ARCHIVAR)
    fase_ciclo_vida: FaseCicloVida = Field(default=FaseCicloVida.NACIMIENTO)
    
    cadido_id: Optional[UUID] = Field(default=None, foreign_key="catalogocadido.id")
    
    # Relación para acceder al catálogo fácilmente
    catalogo: Optional[CatalogoCadido] = Relationship(back_populates="documentos")

from zoneinfo import ZoneInfo

def get_mexico_time() -> datetime:
    return datetime.now(ZoneInfo("America/Mexico_City"))

class BitacoraTrazabilidad(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    documento_id: UUID = Field(foreign_key="documentoprincipal.id")
    fase_anterior: str = Field(max_length=50)
    fase_nueva: str = Field(max_length=50)
    fecha_transaccion: datetime = Field(default_factory=get_mexico_time)
    descripcion_evento: str = Field(max_length=1000)