"""
Modelos de la base de datos usando SQLAlchemy ORM.

Cada clase aquí representa una tabla en PostgreSQL. SQLAlchemy automáticamente
crea las tablas basándose en estas definiciones cuando ejecutamos el script
de inicialización de la base de datos.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import declarative_base

# Base es la clase padre de todos nuestros modelos.
# Cuando heredamos de Base, SQLAlchemy sabe que esta clase representa una tabla.
Base = declarative_base()

class PixelEvent(Base):
    """
    Tabla que registra cada evento de píxel pintado.
    
    Esta tabla usa un patrón de "event sourcing", donde guardamos cada cambio
    como un evento separado en vez de solo el estado actual. Esto nos permite:
    1. Ver el historial completo de cada píxel
    2. Saber quién pintó qué y cuándo
    3. Reconstruir el canvas a cualquier punto en el tiempo
    4. Generar estadísticas y heatmaps
    """
    __tablename__ = "pixel_events"

    # Columnas de la tabla
    # Column() define cada campo, especificando el tipo de dato y restricciones

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # primary_key=True: Esta columna identifica únicamente cada fila
    # index=True: PostgreSQL crea un índice para búsquedas rápidas por ID
    # autoincrement=True: PostgreSQL asigna automáticamente números secuenciales

    x = Column(Integer, nullable=False)
    # nullable=False: Este campo es obligatorio, no puede ser NULL
    # Representa la coordenada X del píxel (0 a CANVAS_WIDTH-1)

    y = Column(Integer, nullable=False)
    # nullable=False: Este campo es obligatorio, no puede ser NULL
    # Representa la coordenada Y del píxel (0 a CANVAS_HEIGHT-1)

    color = Column(String(7), nullable=False)
    # nullable=False: Este campo es obligatorio, no puede ser NULL
    # Representa el color del píxel en formato hex (por ejemplo, '#FF0000' para rojo)

    user_id = Column(String(100), nullable=False)
    # Por ahora usamos un simple string para identificar usuarios
    # En el futuro podríamos cambiarlo a UUID cuando implementemos autenticación real
    # String(100): Suficientemente largo para IPs hasheadas o identificadores de sesión

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # DateTime: Timestamp de cuándo se pintó el píxel
    # default=datetime.utcnow: Si no especificamos un valor, usa la hora actual en UTC
    # Usamos UTC en vez de hora local para evitar problemas con zonas horarias
    
    # Índices compuestos para consultas comunes
    # Un índice compuesto permite búsquedas rápidas por múltiples columnas a la vez
    __table_args__ = (
    # Índice para buscar todos los eventos de un píxel específico
    # Útil para queries como "muéstrame el historial del píxel en (10, 20)"
    Index('idx_pixel_coords', 'x', 'y'),
    
    # Índice para buscar píxeles por usuario
    # Útil para queries como "muéstrame todos los píxeles que pintó este usuario"
    Index('idx_user_id', 'user_id'),
    
    # Índice para ordenar por fecha
    # Útil para queries como "muéstrame los últimos 100 píxeles pintados"
    Index('idx_created_at', 'created_at'),
)

    def __repr__(self):
        """
        Representación en string del objeto para debugging.
        Cuando imprimimos un PixelEvent en la consola, veremos algo legible.
        """
        return f"<PixelEvent(id={self.id}, x={self.x}, y={self.y}, color={self.color})>"



class User(Base):
    """
    Tabla de usuarios (simplificada para el MVP).
    
    Por ahora solo rastreamos información básica. En el futuro podríamos expandir
    esto para incluir autenticación, avatares, estadísticas detalladas, etc.
    """
    __tablename__ = "users"
    
    id = Column(String(100), primary_key=True)
    # Usamos el mismo identificador que en PixelEvent.user_id
    # Podría ser una IP hasheada, un ID de sesión, o eventualmente un UUID
    
    username = Column(String(50), unique=True, nullable=True)
    # username es opcional (nullable=True) porque usuarios anónimos no lo tendrán
    # unique=True: No puede haber dos usuarios con el mismo nombre
    
    total_pixels_placed = Column(Integer, default=0, nullable=False)
    # Contador de cuántos píxeles ha pintado este usuario en total
    # default=0: Los usuarios nuevos empiezan en cero
    
    last_pixel_at = Column(DateTime, nullable=True)
    # Timestamp del último píxel pintado
    # Útil para calcular si el usuario puede pintar de nuevo (cooldown)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Cuándo se creó el registro del usuario
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, pixels={self.total_pixels_placed})>"