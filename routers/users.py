# routers/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user, get_password_hash
from models import Reporte, Usuario
from schemas import ReporteOut, UsuarioUpdate
from sqlalchemy import func
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["Usuarios"])

# ==========================================================
# 📋 Mis reportes
# ==========================================================
@router.get("/mis-reportes", response_model=list[ReporteOut])
def obtener_mis_reportes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    reportes = db.query(Reporte).filter(Reporte.usuario_id == current_user.id).all()
    return reportes

# ==========================================================
# 📊 Estadísticas personales del usuario
# ==========================================================
@router.get("/estadisticas")
def obtener_estadisticas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    resultados = (
        db.query(
            Reporte.ubicacion,
            func.count(Reporte.id)
        )
        .filter(Reporte.usuario_id == current_user.id)
        .group_by(Reporte.ubicacion)
        .all()
    )

    zonas = []
    cantidad = []

    for ubicacion, total in resultados:
        zonas.append(ubicacion)
        cantidad.append(total)

    return {
        "zonas": zonas,
        "cantidad": cantidad
    }

# ==========================================================
# 👤 Actualizar perfil
# ==========================================================
@router.put("/actualizar-perfil")
def actualizar_perfil(
    datos: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if datos.nombre:
        current_user.nombre = datos.nombre
    if datos.password:
        current_user.password = get_password_hash(datos.password)
    if datos.rol:
        current_user.rol = datos.rol  # opcional, normalmente solo admin debería cambiar roles

    db.commit()
    db.refresh(current_user)
    return {"mensaje": "Perfil actualizado con éxito."}
