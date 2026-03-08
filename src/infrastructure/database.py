# src/infrastructure/database.py
from sqlmodel import SQLModel, create_engine, Session
# Importamos nuestras entidades para que SQLModel las registre
from src.domain.entities import DocumentoPrincipal 

# Usaremos SQLite para desarrollo (igual que EF Core InMemory/LocalDB)
sqlite_file_name = "cadido_database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# echo=True imprime las consultas SQL en consola (útil para depurar)
engine = create_engine(sqlite_url, echo=True)

def crear_base_datos_y_tablas():
    """Equivalente a Entity Framework Update-Database / EnsureCreated"""
    SQLModel.metadata.create_all(engine)

def obtener_sesion():
    """Equivalente a inyectar el DbContext o UnitOfWork"""
    with Session(engine) as session:
        yield session