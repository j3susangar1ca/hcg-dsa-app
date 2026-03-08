import hashlib
import hmac
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import StrPath

def generar_hash_sha256(ruta_archivo: "StrPath") -> str:
    """
    Genera hash SHA-256 de archivo en bloques de 4KB.
    """
    path = Path(ruta_archivo)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no existe: {path}")
        
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(4096):
            sha256.update(chunk)
            
    return sha256.hexdigest().lower()

def validar_integridad(ruta_archivo: "StrPath", hash_original: str) -> bool:
    """Comparación segura contra timing attacks."""
    try:
        hash_actual = generar_hash_sha256(ruta_archivo)
        return hmac.compare_digest(hash_actual, hash_original.lower())
    except (FileNotFoundError, PermissionError):
        return False