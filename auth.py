from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
from models import Usuario as User
from pydantic import BaseModel, EmailStr
from schemas import UsuarioOut

# Configuración de JWT
SECRET_KEY = "mi_clave_super_secreta"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Inicializar router
router = APIRouter(prefix="/auth", tags=["Auth"])

# Configuración de bcrypt y OAuth2
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Funciones de seguridad
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Obtener usuario actual desde el token
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# Ruta para iniciar sesión
@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Modelo para registro
class RegistroUsuario(BaseModel):
    nombre: str
    email: EmailStr
    password: str

# Ruta para registrar nuevos usuarios
@router.post("/register")
def registrar_usuario(datos: RegistroUsuario, db: Session = Depends(get_db)):
    if not datos.nombre or not datos.password:
        raise HTTPException(status_code=400, detail="Todos los campos son obligatorios.")

    usuario_existente = db.query(User).filter(User.email == datos.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    
    nuevo_usuario = User(
        nombre=datos.nombre,
        email=datos.email,
        password=get_password_hash(datos.password),
        rol="usuario"
    )
    db.add(nuevo_usuario)
    db.commit()
    return {"mensaje": "Usuario registrado con éxito."}

# Ruta para obtener perfil del usuario actual
@router.get("/me", response_model=UsuarioOut)
def obtener_mi_perfil(current_user: User = Depends(get_current_user)):
    return current_user
