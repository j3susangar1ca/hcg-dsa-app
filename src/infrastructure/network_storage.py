# src/infrastructure/network_storage.py
import os
import shutil
import datetime
from uuid import uuid4

class NetworkStorageManager:
    def __init__(self):
        # Rutas basadas en tu implementación original
        self._ruta_temporal_base = os.path.join(os.environ.get('TEMP', '/tmp'), "GestionDocumental")
        self._ruta_definitiva_base = r"\\10.2.1.92\FAA_divserv_admvos\CORRESPONDENCIA" # Tu IP real detectada en los logs
        
        if not os.path.exists(self._ruta_temporal_base):
            os.makedirs(self._ruta_temporal_base)

    def generar_nombre_convencional(self, codigo_cadido: str, anio: int, folio: str) -> str:
        # Replicamos la lógica de C#
        return f"{codigo_cadido}_{anio}_{folio}.pdf"

    def mover_a_definitivo(self, ruta_temporal: str, subserie: str, anio: int, folio: str) -> str:
        """Equivalente a MoverADefinitivoAsync"""
        nombre_final = self.generar_nombre_convencional(subserie.replace(" ", "_"), anio, folio)
        carpeta_destino = os.path.join(self._ruta_definitiva_base, str(anio), subserie.replace(" ", "_"))
        
        if not os.path.exists(carpeta_destino):
            os.makedirs(carpeta_destino)

        ruta_final = os.path.join(carpeta_destino, nombre_final)
        
        if os.path.exists(ruta_final):
            raise FileExistsError(f"El archivo ya existe en el destino: {ruta_final}")

        # Movimiento de archivo (Equivalente a File.MoveAsync)
        shutil.move(ruta_temporal, ruta_final)
        return ruta_final
