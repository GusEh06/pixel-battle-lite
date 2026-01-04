"""
Sistema de rate limiting (cooldown) para píxeles.

Controla con qué frecuencia los usuarios pueden pintar píxeles.
Implementa un cooldown simple basado en timestamps en la base de datos.

En una versión más avanzada, esto se haría con Redis para mejor rendimiento,
pero para el MVP usar la base de datos PostgreSQL es suficiente.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Tuple


class RateLimiter:
    """
    Gestor de rate limiting para píxeles.
    
    Implementa un cooldown simple: los usuarios deben esperar X segundos
    entre cada píxel que pintan.
    
    Attributes:
        cooldown_seconds: Tiempo de espera entre píxeles (en segundos)
    """
    
    def __init__(self, cooldown_seconds: int = 30):
        """
        Inicializa el rate limiter.
        
        Args:
            cooldown_seconds: Segundos de espera entre píxeles (default: 30)
        """
        self.cooldown_seconds = cooldown_seconds
    
    def check_rate_limit(self, user_id: str, db: Session) -> Tuple[bool, int]:
        """
        Verifica si un usuario puede pintar un píxel ahora.
        
        Consulta la base de datos para ver cuándo fue el último píxel
        del usuario y calcula si ya pasó el tiempo de cooldown.
        
        Args:
            user_id: Identificador del usuario
            db: Sesión de base de datos
        
        Returns:
            Tupla de (puede_pintar, segundos_restantes)
            - puede_pintar: True si el usuario puede pintar ahora
            - segundos_restantes: Segundos que debe esperar (0 si puede pintar)
        """
        from .models import User
        
        # Buscar el usuario en la base de datos
        user = db.query(User).filter(User.id == user_id).first()
        
        # Si el usuario no existe o nunca ha pintado, puede pintar
        if not user or not user.last_pixel_at:
            return True, 0
        
        # Calcular cuánto tiempo ha pasado desde el último píxel
        time_since_last_pixel = datetime.utcnow() - user.last_pixel_at
        seconds_elapsed = time_since_last_pixel.total_seconds()
        
        # Si ya pasó el tiempo de cooldown, puede pintar
        if seconds_elapsed >= self.cooldown_seconds:
            return True, 0
        
        # Calcular cuántos segundos faltan
        seconds_remaining = int(self.cooldown_seconds - seconds_elapsed)
        
        return False, seconds_remaining
    
    def record_pixel_placement(self, user_id: str, db: Session) -> None:
        """
        Registra que un usuario acaba de pintar un píxel.
        
        Actualiza el timestamp del último píxel del usuario.
        Este método debe llamarse DESPUÉS de crear el pixel_event exitosamente.
        
        Args:
            user_id: Identificador del usuario
            db: Sesión de base de datos
        """
        # Esta función ya no hace nada porque update_user_pixel_stats
        # en crud.py ya actualiza el last_pixel_at
        # La dejamos por si en el futuro queremos agregar lógica adicional aquí
        pass