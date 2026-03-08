# src/infrastructure/network_storage.py
import os
import shutil
from datetime import datetime
from pathlib import Path

class NetworkStorageManager:
    def __init__(self):
        # Ruta detectada en tus logs de C#
        self.ruta_base = Path(r"\\10.2.1.92\FAA_divserv_admvos\CORRESPONDENCIA")

    def mover_a_archivo_final(self, ruta_origen: str | Path, subserie: str, folio: str) -> str:
        anio = datetime.now().year
        # Crear estructura: \\10.2.1.92\...\2026\Correspondencia_General
        subserie_clean = subserie.replace(" ", "_")
        carpeta_destino = self.ruta_base / str(anio) / subserie_clean
        
        carpeta_destino.mkdir(parents=True, exist_ok=True)

        # Nombre: CORRESPONDENCIA_GENERAL_2026_FOL-123.pdf
        nombre_final = f"{subserie_clean}_{anio}_{folio}.pdf"
        ruta_destino = carpeta_destino / nombre_final

        # Mover físicamente
        shutil.move(str(ruta_origen), str(ruta_destino))
        return str(ruta_destino)
