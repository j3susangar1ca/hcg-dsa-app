import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from .config import Settings

@contextmanager
def windows_file_operation(path: Path, max_retries: int = 3):
    """Context manager para operaciones de archivo con reintentos en Windows."""
    for attempt in range(max_retries):
        try:
            yield path
            break
        except PermissionError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.5 * (attempt + 1))
        except OSError as e:
            if hasattr(e, 'winerror') and e.winerror == 32:  # ERROR_SHARING_VIOLATION
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.5)
            else:
                raise

class NetworkStorageManager:
    def __init__(self, base_path: Path | None = None):
        self.ruta_base = base_path or Settings().network_base_path

    def _construir_ruta_destino(self, subserie: str, folio: str) -> Path:
        anio = datetime.now().year
        subserie_clean = subserie.replace(" ", "_")
        carpeta_destino = self.ruta_base / str(anio) / subserie_clean
        carpeta_destino.mkdir(parents=True, exist_ok=True)
        nombre_final = f"{subserie_clean}_{anio}_{folio}.pdf"
        return carpeta_destino / nombre_final

    def mover_a_archivo_final(
        self, 
        ruta_origen: str | Path, 
        subserie: str, 
        folio: str
    ) -> str:
        origen = Path(ruta_origen)
        destino = self._construir_ruta_destino(subserie, folio)
        
        with windows_file_operation(destino):
            shutil.copy2(origen, destino)
            origen.unlink()
            
        return str(destino)
