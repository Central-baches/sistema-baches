# crear_usuario.py
from database import SessionLocal
from models import Usuario
from auth import get_password_hash

db = SessionLocal()

nuevo_usuario = Usuario(
    nombre="Admin",
    email="admin@example.com",
    password=get_password_hash("123456"),
    rol="admin"
)

db.add(nuevo_usuario)
db.commit()
db.close()
print("Usuario creado con éxito.")
