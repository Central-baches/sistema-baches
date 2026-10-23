from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from models import Usuario, Reporte
from schemas import UsuarioOut, UsuarioUpdate, ReporteUpdate, ReporteOut
from database import get_db
from auth import get_current_user
import csv
import io

router = APIRouter(prefix="/admin", tags=["Administración"])

# ----------- Verificación de rol -----------
def verificar_admin(usuario: Usuario = Depends(get_current_user)):
    if usuario.rol != "admin":
        raise HTTPException(status_code=403, detail="Acceso restringido a administradores")
    return usuario

# ----------- CRUD de Usuarios -----------
@router.get("/usuarios", response_model=list[UsuarioOut], dependencies=[Depends(verificar_admin)])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).all()

@router.get("/usuarios/{usuario_id}", response_model=UsuarioOut, dependencies=[Depends(verificar_admin)])
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@router.put("/usuarios/{usuario_id}", response_model=UsuarioOut, dependencies=[Depends(verificar_admin)])
def actualizar_usuario(usuario_id: int, datos: UsuarioUpdate, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    for key, value in datos.dict(exclude_unset=True).items():
        setattr(usuario, key, value)
    db.commit()
    db.refresh(usuario)
    return usuario

@router.delete("/usuarios/{usuario_id}", dependencies=[Depends(verificar_admin)])
def eliminar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(usuario)
    db.commit()
    return {"mensaje": "Usuario eliminado"}

# ----------- CRUD de Reportes -----------
@router.get("/reportes", dependencies=[Depends(verificar_admin)])
def listar_reportes(db: Session = Depends(get_db)):
    reportes = db.query(Reporte).all()
    return [
        {
            "id": r.id,
            "tipo": r.tipo,
            "fecha": r.fecha,
            "ubicacion": r.ubicacion,
            "usuario_id": r.usuario_id,
            "usuario_nombre": r.usuario.nombre if r.usuario else "Desconocido",
            "usuario_email": r.usuario.email if r.usuario else "N/A"
        }
        for r in reportes
    ]

@router.get("/reportes/{reporte_id}", response_model=ReporteOut, dependencies=[Depends(verificar_admin)])
def obtener_reporte(reporte_id: int, db: Session = Depends(get_db)):
    reporte = db.query(Reporte).get(reporte_id)
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return reporte

@router.put("/reportes/{reporte_id}", response_model=ReporteOut, dependencies=[Depends(verificar_admin)])
def actualizar_reporte(reporte_id: int, datos: ReporteUpdate, db: Session = Depends(get_db)):
    reporte = db.query(Reporte).get(reporte_id)
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    for key, value in datos.dict().items():
        setattr(reporte, key, value)
    db.commit()
    db.refresh(reporte)
    return reporte

@router.delete("/reportes/{reporte_id}", dependencies=[Depends(verificar_admin)])
def eliminar_reporte(reporte_id: int, db: Session = Depends(get_db)):
    reporte = db.query(Reporte).get(reporte_id)
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    db.delete(reporte)
    db.commit()
    return {"mensaje": "Reporte eliminado"}

# ----------- Dashboard de estadísticas -----------
@router.get("/dashboard", dependencies=[Depends(verificar_admin)])
def obtener_estadisticas(db: Session = Depends(get_db)):
    total_usuarios = db.query(Usuario).count()
    total_reportes = db.query(Reporte).count()
    tipos = db.query(Reporte.tipo).distinct().all()
    return {
        "usuarios": total_usuarios,
        "reportes": total_reportes,
        "tipos_de_reportes": [t[0] for t in tipos]
    }

# ----------- Exportación de reportes a CSV -----------
@router.get("/admin_reportes/csv", dependencies=[Depends(verificar_admin)])
def exportar_reportes_csv(db: Session = Depends(get_db)):
    reportes = db.query(Reporte).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["ID", "Tipo", "Fecha", "Ubicación", "Usuario"])

    for r in reportes:
        writer.writerow([
            r.id,
            r.tipo,
            r.fecha.strftime("%Y-%m-%d %H:%M:%S") if r.fecha else "",
            r.ubicacion,
            r.usuario.nombre if r.usuario else "Desconocido"
        ])

    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=reportes.csv"
        }
    )