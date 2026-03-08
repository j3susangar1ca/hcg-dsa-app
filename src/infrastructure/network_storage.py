# src/infrastructure/network_storage.py
import os
import shutil
from datetime import datetime

class NetworkStorageManager:
    def __init__(self):
        # Ruta detectada en tus logs de C#
        self.ruta_base = r"\\10.2.1.92\FAA_divserv_admvos\CORRESPONDENCIA"

    def mover_a_archivo_final(self, ruta_origen, subserie, folio) -> str:
        anio = datetime.now().year
        # Crear estructura: \\10.2.1.92\...\2026\Correspondencia_General
        subserie_clean = subserie.replace(" ", "_")
        carpeta_destino = os.path.join(self.ruta_base, str(anio), subserie_clean)
        
        if not os.path.exists(carpeta_destino):
            os.makedirs(carpeta_destino)

        # Nombre: CORRESPONDENCIA_GENERAL_2026_FOL-123.pdf
        nombre_final = f"{subserie_clean}_{anio}_{folio}.pdf"
        ruta_destino = os.path.join(carpeta_destino, nombre_final)

        # Mover físicamente
        shutil.move(ruta_origen, ruta_destino)
        return ruta_destino
