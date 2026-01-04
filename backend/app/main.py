"""
Aplicación principal de FastAPI para Pixel Canvas Lite.

Este es el punto de entrada de la aplicación. Define todos los endpoints HTTP
que los clientes pueden llamar para interactuar con el canvas.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os
from dotenv import load_dotenv

from . import crud, models, schemas
from .database import get_db, engine
from .rate_limiter import RateLimiter

# Cargar variables de entorno
load_dotenv()

# Crear las tablas en la base de datos si no existen
# Esto se ejecuta automáticamente cuando arranca la aplicación
# En producción usaríamos Alembic en su lugar, pero para el MVP esto funciona bien
models.Base.metadata.create_all(bind=engine)

# Crear la instancia de la aplicación FastAPI
app = FastAPI(
    title="Pixel Canvas Lite API",
    description="API para un canvas colaborativo de píxeles en tiempo real",
    version="1.0.0",
    docs_url="/docs",  # Documentación interactiva en /docs
    redoc_url="/redoc",  # Documentación alternativa en /redoc
)

# Configurar CORS (Cross-Origin Resource Sharing)
# Esto permite que el frontend (que correrá en un puerto diferente) pueda
# hacer peticiones a la API sin ser bloqueado por las políticas de seguridad del navegador
app.add_middleware(
    CORSMiddleware,
    # En desarrollo permitimos todos los orígenes
    # En producción deberías especificar solo los orígenes permitidos
    allow_origins=["*"],  # En producción: ["https://tudominio.com"]
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Permite todos los headers HTTP
)

# Obtener configuración del canvas desde variables de entorno
CANVAS_WIDTH = int(os.getenv("CANVAS_WIDTH", "32"))
CANVAS_HEIGHT = int(os.getenv("CANVAS_HEIGHT", "32"))
PIXEL_COOLDOWN_SECONDS = int(os.getenv("PIXEL_COOLDOWN_SECONDS", "30"))

# Instancia global del rate limiter
# Esta instancia se comparte entre todas las peticiones
rate_limiter = RateLimiter(cooldown_seconds=PIXEL_COOLDOWN_SECONDS)


@app.get("/", tags=["General"])
async def root():
    """
    Endpoint raíz de la API.
    
    Retorna información básica sobre la API. Útil para verificar que el servidor
    está corriendo correctamente.
    """
    return {
        "message": "Bienvenido a Pixel Canvas Lite API",
        "version": "1.0.0",
        "docs": "/docs",
        "canvas_size": f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}",
        "cooldown": f"{PIXEL_COOLDOWN_SECONDS}s"
    }


@app.get(
    "/api/canvas/info",
    response_model=schemas.CanvasInfoResponse,
    tags=["Canvas"]
)
async def get_canvas_info(db: Session = Depends(get_db)):
    """
    Obtiene información general del canvas sin retornar todos los píxeles.
    
    Este endpoint es ligero y rápido. Útil para mostrar estadísticas generales
    en la interfaz sin tener que cargar el canvas completo.
    
    Returns:
        Información del canvas: dimensiones, total de píxeles pintados,
        usuarios activos, y tiempo de cooldown.
    """
    total_pixels = crud.get_total_pixels_count(db)
    active_users = crud.get_active_users_count(db, since_hours=24)
    
    return schemas.CanvasInfoResponse(
        width=CANVAS_WIDTH,
        height=CANVAS_HEIGHT,
        total_pixels_painted=total_pixels,
        active_users_24h=active_users,
        cooldown_seconds=PIXEL_COOLDOWN_SECONDS
    )


@app.get(
    "/api/canvas/state",
    response_model=schemas.CanvasStateResponse,
    tags=["Canvas"]
)
async def get_canvas_state(db: Session = Depends(get_db)):
    """
    Obtiene el estado completo actual del canvas.
    
    Este endpoint retorna todos los píxeles que han sido pintados.
    Para un canvas de 32x32, esto podría ser hasta 1,024 píxeles.
    
    El frontend debe llamar este endpoint una vez al cargar la página
    para obtener el estado inicial, y luego actualizarse con WebSocket
    (que implementaremos después) o polling.
    
    Returns:
        Estado completo del canvas con todos los píxeles pintados.
    """
    canvas_state = crud.get_current_canvas_state(db, CANVAS_WIDTH, CANVAS_HEIGHT)
    
    # Convertir el diccionario a una lista de PixelInfo
    pixels = [
        schemas.PixelInfo(
            x=x,
            y=y,
            color=pixel_data['color'],
            user_id=pixel_data['user_id'],
            timestamp=pixel_data['timestamp']
        )
        for (x, y), pixel_data in canvas_state.items()
    ]
    
    return schemas.CanvasStateResponse(
        width=CANVAS_WIDTH,
        height=CANVAS_HEIGHT,
        pixels=pixels,
        total_pixels=len(pixels)
    )


@app.get(
    "/api/canvas/pixel/{x}/{y}",
    response_model=schemas.PixelInfo,
    tags=["Canvas"]
)
async def get_pixel(
    x: int,
    y: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene información de un píxel específico.
    
    Args:
        x: Coordenada X del píxel
        y: Coordenada Y del píxel
    
    Returns:
        Información del píxel: color, usuario que lo pintó, timestamp
    
    Raises:
        404: Si el píxel nunca ha sido pintado
        400: Si las coordenadas están fuera de rango
    """
    # Validar coordenadas
    if x < 0 or x >= CANVAS_WIDTH or y < 0 or y >= CANVAS_HEIGHT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coordenadas fuera de rango. El canvas es {CANVAS_WIDTH}x{CANVAS_HEIGHT}"
        )
    
    pixel = crud.get_pixel_at(db, x, y)
    
    if not pixel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El píxel en ({x}, {y}) nunca ha sido pintado"
        )
    
    return schemas.PixelInfo(**pixel)


@app.post(
    "/api/pixels",
    response_model=schemas.PixelPlaceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Pixels"]
)
async def place_pixel(
    pixel_request: schemas.PixelPlaceRequest,
    db: Session = Depends(get_db),
    # En una aplicación real, obtendríamos el user_id de un token de autenticación
    # Por ahora usamos un placeholder
    user_id: str = "anonymous_user"
):
    """
    Pinta un píxel en el canvas.
    
    Este es el endpoint principal para la interacción del usuario.
    Valida coordenadas, verifica el cooldown, y registra el píxel en la BD.
    
    Args:
        pixel_request: Datos del píxel a pintar (x, y, color)
        user_id: Identificador del usuario (por ahora hardcoded)
    
    Returns:
        Confirmación del píxel pintado con información del cooldown
    
    Raises:
        400: Si las coordenadas están fuera de rango
        429: Si el usuario está en cooldown (demasiados píxeles muy rápido)
    """
    x = pixel_request.x
    y = pixel_request.y
    color = pixel_request.color
    
    # Validar que las coordenadas estén dentro del canvas
    if x < 0 or x >= CANVAS_WIDTH or y < 0 or y >= CANVAS_HEIGHT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_COORDINATES",
                "message": f"Coordenadas fuera de rango. El canvas es {CANVAS_WIDTH}x{CANVAS_HEIGHT}",
                "details": {
                    "max_x": CANVAS_WIDTH - 1,
                    "max_y": CANVAS_HEIGHT - 1,
                    "received_x": x,
                    "received_y": y
                }
            }
        )
    
    # Verificar cooldown del usuario
    can_place, cooldown_remaining = rate_limiter.check_rate_limit(user_id, db)
    
    if not can_place:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "COOLDOWN_ACTIVE",
                "message": f"Debes esperar {cooldown_remaining} segundos antes de pintar otro píxel",
                "details": {
                    "cooldown_remaining": cooldown_remaining
                }
            }
        )
    
    # Crear el evento de píxel en la base de datos
    pixel_event = crud.create_pixel_event(
        db=db,
        x=x,
        y=y,
        color=color,
        user_id=user_id
    )
    
    # Actualizar estadísticas del usuario
    crud.update_user_pixel_stats(db, user_id)
    
    # Registrar que este usuario acaba de pintar un píxel (para el cooldown)
    rate_limiter.record_pixel_placement(user_id, db)
    
    return schemas.PixelPlaceResponse(
        success=True,
        message="Píxel pintado exitosamente",
        pixel={
            "x": pixel_event.x,
            "y": pixel_event.y,
            "color": pixel_event.color,
            "user_id": pixel_event.user_id,
            "timestamp": pixel_event.created_at.isoformat()
        },
        cooldown_remaining=PIXEL_COOLDOWN_SECONDS
    )


@app.get(
    "/api/pixels/recent",
    response_model=List[schemas.PixelInfo],
    tags=["Pixels"]
)
async def get_recent_pixels(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Obtiene los píxeles pintados más recientemente.
    
    Útil para mostrar un feed de actividad reciente o para actualizar
    el canvas sin tener que cargar todo el estado.
    
    Args:
        limit: Número máximo de píxeles a retornar (por defecto 100)
    
    Returns:
        Lista de píxeles ordenados del más reciente al más antiguo
    """
    # Limitar el límite máximo para evitar queries muy pesadas
    if limit > 500:
        limit = 500
    
    recent_pixels = crud.get_recent_pixels(db, limit=limit)
    
    return [schemas.PixelInfo(**pixel) for pixel in recent_pixels]


@app.get(
    "/api/pixels/history/{x}/{y}",
    response_model=schemas.PixelHistoryResponse,
    tags=["Pixels"]
)
async def get_pixel_history(
    x: int,
    y: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial completo de un píxel específico.
    
    Muestra todos los cambios que ha tenido un píxel a lo largo del tiempo.
    Útil para ver "guerras" de píxeles o estadísticas de una coordenada.
    
    Args:
        x: Coordenada X
        y: Coordenada Y
        limit: Máximo de eventos históricos a retornar
    
    Returns:
        Historial de cambios ordenado del más reciente al más antiguo
    """
    # Validar coordenadas
    if x < 0 or x >= CANVAS_WIDTH or y < 0 or y >= CANVAS_HEIGHT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coordenadas fuera de rango"
        )
    
    history = crud.get_pixel_history(db, x, y, limit=limit)
    
    return schemas.PixelHistoryResponse(
        x=x,
        y=y,
        history=history,
        total_changes=len(history)
    )


@app.get(
    "/api/users/{user_id}/stats",
    response_model=schemas.UserStatsResponse,
    tags=["Users"]
)
async def get_user_stats(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas de un usuario específico.
    
    Args:
        user_id: Identificador del usuario
    
    Returns:
        Estadísticas del usuario: píxeles pintados, último píxel, etc.
    
    Raises:
        404: Si el usuario no existe
    """
    stats = crud.get_user_stats(db, user_id)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario '{user_id}' no encontrado"
        )
    
    return schemas.UserStatsResponse(**stats)


@app.get(
    "/api/health",
    tags=["General"]
)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    
    Verifica que la aplicación y la base de datos estén funcionando correctamente.
    Útil para monitoreo y balanceadores de carga.
    
    Returns:
        Estado del sistema
    """
    try:
        # Intentar hacer una query simple a la BD para verificar conectividad
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "canvas_size": f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}"
    }


# Manejador de errores personalizado para HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    Manejador personalizado de excepciones HTTP.
    
    Formatea todas las respuestas de error de manera consistente.
    """
    return {
        "success": False,
        "error": exc.detail if isinstance(exc.detail, dict) else {"message": exc.detail},
        "status_code": exc.status_code
    }


if __name__ == "__main__":
    # Este bloque se ejecuta solo si ejecutas el archivo directamente
    # No se ejecuta cuando uvicorn importa el módulo
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # Escuchar en todas las interfaces de red
        port=8000,
        reload=True  # Auto-reload cuando cambies código (solo desarrollo)
    )