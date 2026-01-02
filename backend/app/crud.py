"""
Operaciones CRUD (Create, Read, Update, Delete) para la base de datos.

Este módulo contiene todas las funciones que interactúan directamente con PostgreSQL.
Separar estas operaciones en su propio archivo hace el código más organizado y testeable.

Las funciones aquí reciben una sesión de SQLAlchemy y retornan objetos de modelos
o datos procesados. No manejan HTTP directamente, eso es responsabilidad de los endpoints.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from . import models


def get_current_canvas_state(db: Session, width: int, height: int) -> Dict[Tuple[int, int], dict]:
    """
    Obtiene el estado actual completo del canvas.
    
    Esta función construye el canvas desde cero leyendo el historial de eventos
    y tomando el último evento para cada coordenada. Es relativamente costosa
    computacionalmente, por eso en el futuro podríamos agregar caché en Redis.
    
    Args:
        db: Sesión activa de SQLAlchemy
        width: Ancho del canvas en píxeles
        height: Alto del canvas en píxeles
    
    Returns:
        Diccionario donde la clave es (x, y) y el valor es un dict con
        información del píxel: {color, user_id, timestamp}
    """
    # Subconsulta para obtener el ID del evento más reciente para cada coordenada
    # Esta es una técnica SQL común llamada "grouped maximum" o "latest record per group"
    subquery = (
        db.query(
            models.PixelEvent.x,
            models.PixelEvent.y,
            func.max(models.PixelEvent.id).label('max_id')
        )
        .group_by(models.PixelEvent.x, models.PixelEvent.y)
        .subquery()
    )
    
    # Query principal que obtiene los eventos completos usando los IDs de la subconsulta
    # JOIN con la subconsulta para obtener solo los eventos más recientes
    latest_pixels = (
        db.query(models.PixelEvent)
        .join(
            subquery,
            (models.PixelEvent.x == subquery.c.x) &
            (models.PixelEvent.y == subquery.c.y) &
            (models.PixelEvent.id == subquery.c.max_id)
        )
        .all()
    )
    
    # Construir el diccionario del canvas
    canvas_state = {}
    for pixel in latest_pixels:
        canvas_state[(pixel.x, pixel.y)] = {
            'color': pixel.color,
            'user_id': pixel.user_id,
            'timestamp': pixel.created_at.isoformat()
        }
    
    return canvas_state


def get_pixel_at(db: Session, x: int, y: int) -> Optional[dict]:
    """
    Obtiene el estado actual de un píxel específico.
    
    Args:
        db: Sesión de base de datos
        x: Coordenada X del píxel
        y: Coordenada Y del píxel
    
    Returns:
        Dict con información del píxel o None si nunca se ha pintado
    """
    # Buscar el evento más reciente para estas coordenadas
    # order_by(desc()) ordena del más reciente al más antiguo
    # first() retorna el primer resultado o None si no hay resultados
    latest_event = (
        db.query(models.PixelEvent)
        .filter(models.PixelEvent.x == x, models.PixelEvent.y == y)
        .order_by(desc(models.PixelEvent.created_at))
        .first()
    )
    
    if not latest_event:
        return None
    
    return {
        'x': latest_event.x,
        'y': latest_event.y,
        'color': latest_event.color,
        'user_id': latest_event.user_id,
        'timestamp': latest_event.created_at.isoformat()
    }


def create_pixel_event(
    db: Session,
    x: int,
    y: int,
    color: str,
    user_id: str
) -> models.PixelEvent:
    """
    Crea un nuevo evento de píxel en la base de datos.
    
    Esta función registra que un usuario pintó un píxel en una posición específica.
    No valida coordenadas ni cooldowns, eso debe hacerse antes de llamar esta función.
    
    Args:
        db: Sesión de base de datos
        x: Coordenada X (debe estar validada previamente)
        y: Coordenada Y (debe estar validada previamente)
        color: Color en formato hex (debe estar validado previamente)
        user_id: Identificador del usuario
    
    Returns:
        El objeto PixelEvent recién creado
    """
    # Crear instancia del modelo
    pixel_event = models.PixelEvent(
        x=x,
        y=y,
        color=color,
        user_id=user_id,
        # created_at se asigna automáticamente por el default en el modelo
    )
    
    # Agregar a la sesión (esto aún no escribe en la BD)
    db.add(pixel_event)
    
    # Hacer commit para guardar en PostgreSQL
    # Si hay algún error, SQLAlchemy automáticamente hace rollback
    db.commit()
    
    # Refrescar el objeto para obtener valores asignados por la BD (como el ID)
    db.refresh(pixel_event)
    
    return pixel_event


def get_pixel_history(
    db: Session,
    x: int,
    y: int,
    limit: int = 50
) -> List[dict]:
    """
    Obtiene el historial de cambios de un píxel específico.
    
    Útil para ver quiénes han pintado en una posición a lo largo del tiempo.
    
    Args:
        db: Sesión de base de datos
        x: Coordenada X
        y: Coordenada Y
        limit: Máximo número de eventos a retornar (por defecto 50)
    
    Returns:
        Lista de eventos ordenados del más reciente al más antiguo
    """
    events = (
        db.query(models.PixelEvent)
        .filter(models.PixelEvent.x == x, models.PixelEvent.y == y)
        .order_by(desc(models.PixelEvent.created_at))
        .limit(limit)
        .all()
    )
    
    return [
        {
            'color': event.color,
            'user_id': event.user_id,
            'timestamp': event.created_at.isoformat()
        }
        for event in events
    ]


def get_recent_pixels(db: Session, limit: int = 100) -> List[dict]:
    """
    Obtiene los píxeles pintados más recientemente en todo el canvas.
    
    Útil para mostrar actividad reciente o un feed en tiempo real.
    
    Args:
        db: Sesión de base de datos
        limit: Número de píxeles recientes a retornar
    
    Returns:
        Lista de eventos de píxeles ordenados del más reciente al más antiguo
    """
    recent = (
        db.query(models.PixelEvent)
        .order_by(desc(models.PixelEvent.created_at))
        .limit(limit)
        .all()
    )
    
    return [
        {
            'x': event.x,
            'y': event.y,
            'color': event.color,
            'user_id': event.user_id,
            'timestamp': event.created_at.isoformat()
        }
        for event in recent
    ]


def get_or_create_user(db: Session, user_id: str) -> models.User:
    """
    Busca un usuario por ID, o lo crea si no existe.
    
    Este patrón "get or create" es muy común en aplicaciones web.
    Garantiza que siempre tendremos un registro de usuario válido.
    
    Args:
        db: Sesión de base de datos
        user_id: Identificador del usuario
    
    Returns:
        El objeto User existente o recién creado
    """
    # Intentar buscar el usuario primero
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    # Si existe, retornarlo
    if user:
        return user
    
    # Si no existe, crear uno nuevo
    new_user = models.User(
        id=user_id,
        username=None,  # Por ahora los usuarios son anónimos
        total_pixels_placed=0,
        last_pixel_at=None
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


def update_user_pixel_stats(db: Session, user_id: str) -> None:
    """
    Actualiza las estadísticas de un usuario después de pintar un píxel.
    
    Incrementa el contador de píxeles totales y actualiza el timestamp
    del último píxel pintado.
    
    Args:
        db: Sesión de base de datos
        user_id: Identificador del usuario
    """
    user = get_or_create_user(db, user_id)
    
    # Incrementar contador
    user.total_pixels_placed += 1
    
    # Actualizar timestamp
    user.last_pixel_at = datetime.utcnow()
    
    # Guardar cambios
    db.commit()


def get_user_stats(db: Session, user_id: str) -> Optional[dict]:
    """
    Obtiene estadísticas de un usuario específico.
    
    Args:
        db: Sesión de base de datos
        user_id: Identificador del usuario
    
    Returns:
        Dict con estadísticas del usuario o None si no existe
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user:
        return None
    
    return {
        'user_id': user.id,
        'username': user.username,
        'total_pixels_placed': user.total_pixels_placed,
        'last_pixel_at': user.last_pixel_at.isoformat() if user.last_pixel_at else None,
        'member_since': user.created_at.isoformat()
    }


def get_total_pixels_count(db: Session) -> int:
    """
    Cuenta el número total de píxeles pintados en todo el canvas.
    
    Returns:
        Número total de eventos de píxeles en la base de datos
    """
    return db.query(func.count(models.PixelEvent.id)).scalar()


def get_active_users_count(db: Session, since_hours: int = 24) -> int:
    """
    Cuenta usuarios que han pintado al menos un píxel en las últimas X horas.
    
    Args:
        db: Sesión de base de datos
        since_hours: Ventana de tiempo en horas (por defecto 24)
    
    Returns:
        Número de usuarios únicos activos
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=since_hours)
    
    # COUNT(DISTINCT user_id) cuenta usuarios únicos
    count = (
        db.query(func.count(func.distinct(models.PixelEvent.user_id)))
        .filter(models.PixelEvent.created_at >= cutoff_time)
        .scalar()
    )
    
    return count