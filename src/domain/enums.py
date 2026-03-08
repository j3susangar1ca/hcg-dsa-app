# src/domain/enums.py
from enum import Enum

class FaseCicloVida(str, Enum):
    NACIMIENTO = "Nacimiento"
    INGRESADO = "Ingresado"
    SELLADO = "Sellado"
    CLASIFICADO = "Clasificado"
    ARCHIVADO = "Archivado"
    RECHAZADO = "Rechazado"

class EstatusAccion(str, Enum):
    RESPUESTA = "Respuesta"
    GESTION = "Gestion"
    AVISO = "Aviso"
    ARCHIVAR = "Archivar"