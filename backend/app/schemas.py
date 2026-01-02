"""
Esquemas de Pydantic para validación y serialización de datos.

Los esquemas definen la forma exacta de los datos que fluyen a través de la API:
- Request schemas: Validan datos que llegan del cliente
- Response schemas: Definen la estructura de datos que enviamos al cliente

Pydantic automáticamente:
1. Valida tipos de datos
2. Convierte tipos cuando es posible (ej: "123" -> 123)
3. Genera errores descriptivos cuando la validación falla
4. Crea documentación automática para FastAPI
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


class PixelPlaceRequest(BaseModel):
    """
    Esquema para la solicitud de pintar un píxel.
    
    Este es el JSON que el cliente debe enviar cuando quiere pintar un píxel.
    Pydantic validará automáticamente que los datos cumplan con estas restricciones.
    
    Ejemplo de JSON válido:
    {
        "x": 15,
        "y": 20,
        "color": "#FF5733"
    }
    """
    
    x: int = Field(
        ...,  # ... significa que este campo es obligatorio
        ge=0,  # ge = greater than or equal (mayor o igual a 0)
        description="Coordenada X del píxel (0-indexed)"
    )
    
    y: int = Field(
        ...,
        ge=0,
        description="Coordenada Y del píxel (0-indexed)"
    )
    
    color: str = Field(
        ...,
        min_length=7,
        max_length=7,
        description="Color en formato hexadecimal (#RRGGBB)"
    )
    
    @field_validator('color')
    @classmethod
    def validate_hex_color(cls, value: str) -> str:
        """
        Validador personalizado para el campo color.
        
        Este método se ejecuta automáticamente después de las validaciones básicas.
        Verifica que el color sea un hexadecimal válido de CSS.
        
        Args:
            value: El valor del campo color que ya pasó las validaciones básicas
        
        Returns:
            El valor en mayúsculas si es válido
        
        Raises:
            ValueError: Si el formato del color no es válido
        """
        # Patrón regex para colores hex: # seguido de exactamente 6 caracteres hex
        # ^ marca el inicio, $ marca el final (debe coincidir exactamente)
        pattern = r'^#[0-9A-Fa-f]{6}$'
        
        if not re.match(pattern, value):
            raise ValueError(
                f"El color '{value}' no es un hexadecimal válido. "
                f"Debe tener el formato #RRGGBB (ej: #FF5733)"
            )
        
        # Retornar en mayúsculas para normalizar (tanto #ff5733 como #FF5733 son válidos)
        return value.upper()
    
    class Config:
        """
        Configuración del esquema Pydantic.
        
        json_schema_extra proporciona ejemplos para la documentación automática.
        Cuando abras /docs en FastAPI, verás estos ejemplos.
        """
        json_schema_extra = {
            "examples": [
                {
                    "x": 15,
                    "y": 20,
                    "color": "#FF5733"
                }
            ]
        }


class PixelPlaceResponse(BaseModel):
    """
    Respuesta exitosa al pintar un píxel.
    
    Este es el JSON que el servidor envía de vuelta después de pintar exitosamente.
    """
    
    success: bool = Field(
        default=True,
        description="Indica si la operación fue exitosa"
    )
    
    message: str = Field(
        default="Píxel pintado exitosamente",
        description="Mensaje descriptivo del resultado"
    )
    
    pixel: dict = Field(
        ...,
        description="Información del píxel pintado"
    )
    
    cooldown_remaining: int = Field(
        default=0,
        description="Segundos hasta que el usuario pueda pintar de nuevo"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "message": "Píxel pintado exitosamente",
                    "pixel": {
                        "x": 15,
                        "y": 20,
                        "color": "#FF5733",
                        "user_id": "anonymous_abc123"
                    },
                    "cooldown_remaining": 30
                }
            ]
        }


class PixelInfo(BaseModel):
    """
    Información sobre un píxel específico.
    
    Usado tanto para respuestas individuales como dentro de listas.
    """
    
    x: int = Field(..., description="Coordenada X")
    y: int = Field(..., description="Coordenada Y")
    color: str = Field(..., description="Color hexadecimal")
    user_id: str = Field(..., description="ID del usuario que pintó este píxel")
    timestamp: str = Field(..., description="Cuándo se pintó (ISO 8601)")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "x": 10,
                    "y": 15,
                    "color": "#3357FF",
                    "user_id": "anonymous_xyz789",
                    "timestamp": "2025-01-15T14:30:00"
                }
            ]
        }


class CanvasStateResponse(BaseModel):
    """
    Respuesta con el estado completo del canvas.
    
    Retorna todos los píxeles que han sido pintados.
    Para un canvas de 32x32, esto podría ser hasta 1,024 píxeles.
    """
    
    width: int = Field(..., description="Ancho del canvas en píxeles")
    height: int = Field(..., description="Alto del canvas en píxeles")
    pixels: List[PixelInfo] = Field(..., description="Lista de todos los píxeles pintados")
    total_pixels: int = Field(..., description="Total de píxeles en el canvas")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "width": 32,
                    "height": 32,
                    "pixels": [
                        {
                            "x": 0,
                            "y": 0,
                            "color": "#FF0000",
                            "user_id": "user1",
                            "timestamp": "2025-01-15T10:00:00"
                        }
                    ],
                    "total_pixels": 1
                }
            ]
        }


class CanvasInfoResponse(BaseModel):
    """
    Información general sobre el canvas sin incluir todos los píxeles.
    
    Útil para un endpoint ligero que solo da metadata.
    """
    
    width: int = Field(..., description="Ancho del canvas")
    height: int = Field(..., description="Alto del canvas")
    total_pixels_painted: int = Field(..., description="Total de píxeles pintados hasta ahora")
    active_users_24h: int = Field(..., description="Usuarios activos en las últimas 24 horas")
    cooldown_seconds: int = Field(..., description="Tiempo de espera entre píxeles")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "width": 32,
                    "height": 32,
                    "total_pixels_painted": 847,
                    "active_users_24h": 23,
                    "cooldown_seconds": 30
                }
            ]
        }


class PixelHistoryResponse(BaseModel):
    """
    Historial de cambios de un píxel específico.
    
    Muestra quién ha pintado en una coordenada a lo largo del tiempo.
    """
    
    x: int = Field(..., description="Coordenada X del píxel")
    y: int = Field(..., description="Coordenada Y del píxel")
    history: List[dict] = Field(..., description="Lista de eventos históricos")
    total_changes: int = Field(..., description="Número total de veces que se pintó este píxel")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "x": 15,
                    "y": 20,
                    "history": [
                        {
                            "color": "#FF5733",
                            "user_id": "user2",
                            "timestamp": "2025-01-15T14:00:00"
                        },
                        {
                            "color": "#33FF57",
                            "user_id": "user1",
                            "timestamp": "2025-01-15T12:00:00"
                        }
                    ],
                    "total_changes": 2
                }
            ]
        }


class UserStatsResponse(BaseModel):
    """
    Estadísticas de un usuario específico.
    """
    
    user_id: str = Field(..., description="Identificador del usuario")
    username: Optional[str] = Field(None, description="Nombre de usuario (si existe)")
    total_pixels_placed: int = Field(..., description="Total de píxeles pintados por este usuario")
    last_pixel_at: Optional[str] = Field(None, description="Última vez que pintó un píxel")
    member_since: str = Field(..., description="Cuándo se registró el usuario")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "user_id": "anonymous_abc123",
                    "username": None,
                    "total_pixels_placed": 12,
                    "last_pixel_at": "2025-01-15T14:30:00",
                    "member_since": "2025-01-15T10:00:00"
                }
            ]
        }


class ErrorResponse(BaseModel):
    """
    Formato estándar para errores.
    
    Usado cuando algo sale mal: validación fallida, cooldown activo, etc.
    """
    
    success: bool = Field(default=False, description="Siempre False para errores")
    error: str = Field(..., description="Tipo de error")
    message: str = Field(..., description="Mensaje descriptivo del error")
    details: Optional[dict] = Field(None, description="Información adicional sobre el error")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": False,
                    "error": "COOLDOWN_ACTIVE",
                    "message": "Debes esperar antes de pintar otro píxel",
                    "details": {
                        "cooldown_remaining": 25
                    }
                }
            ]
        }