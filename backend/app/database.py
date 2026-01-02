"""
Configuración de la base de datos y gestión de sesiones.

Este módulo centraliza toda la lógica de conexión a PostgreSQL usando SQLAlchemy.
Exporta funciones y objetos que el resto de la aplicación usa para interactuar
con la base de datos.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
# Esto hace que las variables definidas en .env estén disponibles vía os.getenv()
load_dotenv()

# Obtener la URL de conexión a la base de datos desde las variables de entorno
# Si no existe DATABASE_URL en el .env, usa un valor por defecto para SQLite
# (útil para tests rápidos sin necesitar PostgreSQL)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./test.db"  # Fallback a SQLite si no hay PostgreSQL configurado
)

# Crear el "engine" de SQLAlchemy
# El engine es el punto de entrada de bajo nivel para todas las interacciones con la BD.
# Piensa en él como el administrador de conexiones que sabe cómo hablar con PostgreSQL.
engine = create_engine(
    DATABASE_URL,
    # connect_args es un diccionario de argumentos específicos del driver de BD
    # Para PostgreSQL normalmente no necesitamos nada especial aquí,
    # pero lo dejamos preparado por si necesitamos configuraciones personalizadas
    connect_args={},
    # echo=True haría que SQLAlchemy imprima todos los SQL queries en la consola
    # Útil para debugging, pero lo dejamos en False por ahora para no saturar los logs
    echo=False,
    # pool_pre_ping=True hace que SQLAlchemy verifique las conexiones antes de usarlas
    # Esto previene errores cuando una conexión se cerró inesperadamente
    pool_pre_ping=True,
)

# Crear una "fábrica" de sesiones
# SessionLocal es una clase (no un objeto) que produce objetos Session cuando la llamamos.
# Cada Session representa una conversación con la base de datos.
SessionLocal = sessionmaker(
    # autocommit=False significa que debemos hacer commit() explícitamente
    # Esto nos da control sobre cuándo los cambios se guardan realmente en la BD
    autocommit=False,
    
    # autoflush=False evita que SQLAlchemy envíe cambios a la BD automáticamente
    # antes de cada query. Preferimos controlar esto manualmente.
    autoflush=False,
    
    # bind=engine conecta esta fábrica de sesiones con nuestro engine de PostgreSQL
    bind=engine,
)

def get_db():
    """
    Generador que proporciona una sesión de base de datos y la cierra automáticamente.
    
    Esta función es un "dependency" de FastAPI. Se usa con la sintaxis:
    
        @app.get("/endpoint")
        def mi_endpoint(db: Session = Depends(get_db)):
            # Aquí 'db' es una sesión activa
            ...
    
    FastAPI automáticamente:
    1. Llama a get_db() para obtener una sesión
    2. Pasa esa sesión a tu función endpoint
    3. Cierra la sesión cuando la función termina (éxito o error)
    
    El patrón try/finally garantiza que la sesión siempre se cierre,
    incluso si hay una excepción. Esto previene "leaks" de conexiones a la BD.
    
    Yields:
        Session: Una sesión activa de SQLAlchemy conectada a PostgreSQL
    """
    # Crear una nueva sesión de base de datos
    db = SessionLocal()
    try:
        # 'yield' pausa la función aquí y entrega la sesión al código que la llamó
        # Cuando ese código termina, la ejecución continúa después del yield
        yield db
    finally:
        # Este bloque SIEMPRE se ejecuta, haya o no haya error
        # Cerramos la sesión para liberar la conexión de vuelta al pool
        db.close()

def init_db():
    """
    Inicializa la base de datos creando todas las tablas definidas en models.py

    Esta función debe ejecutarse una sola vez al configurar el proyecto.
    Lee las clases de modelos (PixelEvent, User) y genera el SQL CREATE TABLE
    correspondiente para cada una.

    Nota: En producción usarías Alembic para migraciones en vez de esta función,
    pero para el MVP esto es más simple y directo.
    """
    # Importamos Base desde models.py
    # La importación está aquí dentro para evitar dependencias circulares
    from .models import Base

    # create_all() inspecciona todas las clases que heredan de Base
    # y ejecuta CREATE TABLE para cada una que no exista ya en PostgreSQL
    Base.metadata.create_all(bind=engine)

    print("✅ Base de datos inicializada correctamente")
    print(f"📊 Tablas creadas en: {DATABASE_URL}")