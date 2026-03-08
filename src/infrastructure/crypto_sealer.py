# src/infrastructure/crypto_sealer.py
import hashlib
import os

class CryptoSealer:
    @staticmethod
    def generar_hash_sha256(ruta_archivo: str) -> str:
        if not os.path.exists(ruta_archivo):
            raise FileNotFoundError(f"Archivo no existe: {ruta_archivo}")
            
        sha256 = hashlib.sha256()
        with open(ruta_archivo, "rb") as f:
            # Leer en bloques por si el PDF es muy pesado
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
                
        return sha256.hexdigest().lower()

    @staticmethod
    def validar_integridad(ruta_archivo: str, hash_original: str) -> bool:
        try:
            hash_actual = CryptoSealer.generar_hash_sha256(ruta_archivo)
            import hmac
            # Comparación segura contra timing attacks (Equivalente a CryptographicOperations.FixedTimeEquals)
            return hmac.compare_digest(hash_actual, hash_original)
        except Exception:
            return False