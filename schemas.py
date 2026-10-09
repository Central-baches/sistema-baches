from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# ==========================================================
# 🧑‍💼 Usuario
# ==========================================================

class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    rol: str = "usuario"  # Valor por defecto

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    rol: Optional[str] = None
    password: Optional[str] = None

class UsuarioOut(UsuarioBase):
    id: int

    class Config:
        orm_mode = True

# ==========================================================
# 🚧 Reporte
# ==========================================================

class ReporteBase(BaseModel):
    tipo: str
    ubicacion: str
    imagen: str  # nombre del archivo o ruta

class ReporteCreate(ReporteBase):
    pass

class ReporteUpdate(BaseModel):
    tipo: Optional[str] = None
    ubicacion: Optional[str] = None
    imagen: Optional[str] = None

class ReporteOut(ReporteBase):
    id: int
    fecha: datetime
    usuario_id: int

    class Config:
        orm_mode = True
