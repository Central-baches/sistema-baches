# models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    password = Column(String(255))
    rol = Column(String(50), default="usuario")  # Puede ser 'usuario' o 'admin'

    reportes = relationship("Reporte", back_populates="usuario")

class Reporte(Base):
    __tablename__ = "reportes"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(100))
    fecha = Column(DateTime, default=datetime.now)
    ubicacion = Column(String(100))
    imagen = Column(String(255))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))

    usuario = relationship("Usuario", back_populates="reportes")
