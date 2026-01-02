"""
Script para inicializar la base de datos.

Ejecuta este script UNA VEZ después de configurar el proyecto para crear
todas las tablas en PostgreSQL.

Uso:
    python backend/init_db.py
"""

from app.database import init_db

if __name__ == "__main__":
    print("🚀 Iniciando configuración de la base de datos...")
    print("=" * 50)
    
    init_db()
    
    print("=" * 50)
    print("🎉 ¡Listo! La base de datos está configurada y lista para usar.")