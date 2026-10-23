# main.py

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Request,
    Depends,
    HTTPException,
    Form,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from ultralytics import YOLO
from datetime import datetime
from dotenv import load_dotenv

import aiosmtplib
import shutil
import os

from email.message import EmailMessage

# ==========================================================
# Importaciones locales
# ==========================================================
from database import get_db
from auth import router as auth_router, get_current_user
from routers import users, baches, admin
from models import Reporte, Usuario

# ==========================================================
# Variables de entorno
# ==========================================================
load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# ==========================================================
# Inicializar FastAPI
# ==========================================================
app = FastAPI(title="Detector de Baches")

# ==========================================================
# Archivos estáticos y plantillas
# ==========================================================
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(directory="templates")

# ==========================================================
# CORS
# ==========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# Incluir routers
# ==========================================================
app.include_router(auth_router)
app.include_router(users.router)
app.include_router(baches.router)
app.include_router(admin.router)

# ==========================================================
# Cargar modelo YOLO
# ==========================================================
if not os.path.exists("best.pt"):
    raise FileNotFoundError(
        "El archivo 'best.pt' no fue encontrado en el directorio raíz."
    )

model = YOLO("best.pt")

# ==========================================================
# Página principal: redirección al login
# ==========================================================
@app.get("/", response_class=HTMLResponse)
async def home():
    return RedirectResponse(url="/login")


# ==========================================================
# Páginas de autenticación
# ==========================================================
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {"request": request}
    )


# ==========================================================
# Menú de usuario
# ==========================================================
@app.get("/user-home", response_class=HTMLResponse)
async def user_home(request: Request):
    return templates.TemplateResponse(
        "user_home.html",
        {"request": request}
    )


@app.get("/index", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@app.get("/mis-reportes", response_class=HTMLResponse)
async def mis_reportes(
    request: Request
):
    return templates.TemplateResponse(
        "mis_reportes.html",
        {
            "request": request
        }
    )


@app.get("/estadisticas", response_class=HTMLResponse)
async def estadisticas(request: Request):
    return templates.TemplateResponse(
        "estadisticas.html",
        {"request": request}
    )


@app.get("/perfil", response_class=HTMLResponse)
async def perfil(request: Request):
    return templates.TemplateResponse(
        "perfil.html",
        {"request": request}
    )


@app.get("/logout")
async def logout():
    return RedirectResponse(url="/login")


# ==========================================================
# Panel de administración
# ==========================================================
@app.get("/admin-panel", response_class=HTMLResponse)
async def admin_panel(request: Request):
    return templates.TemplateResponse(
        "admin.html",
        {"request": request}
    )


@app.get("/admin-home", response_class=HTMLResponse)
async def admin_home(request: Request):
    return templates.TemplateResponse(
        "admin_home.html",
        {"request": request}
    )


@app.get("/admin-usuarios", response_class=HTMLResponse)
async def admin_usuarios(request: Request):
    return templates.TemplateResponse(
        "admin_usuarios.html",
        {"request": request}
    )


@app.get("/admin-dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    reportes = db.query(Reporte).all()

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "reportes": reportes
        }
    )


# ==========================================================
# API protegida para detección de baches y geolocalización
# ==========================================================
@app.post("/api/detect-bache")
async def detect_bache(
    file: UploadFile = File(...),
    latitud: float | None = Form(None),
    longitud: float | None = Form(None),
    precision: float | None = Form(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # ------------------------------------------------------
    # 1. Depuración de datos recibidos
    # ------------------------------------------------------
    print("DEBUG: Archivo =", file.filename)
    print("DEBUG: Tipo de contenido =", file.content_type)
    print("DEBUG: Latitud =", latitud)
    print("DEBUG: Longitud =", longitud)
    print("DEBUG: Precisión =", precision)

    # ------------------------------------------------------
    # 2. Validar archivo
    # ------------------------------------------------------
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="El archivo enviado no es una imagen válida."
        )

    # ------------------------------------------------------
    # 3. Validar coordenadas recibidas
    # ------------------------------------------------------
    if latitud is not None and not -90 <= latitud <= 90:
        raise HTTPException(
            status_code=400,
            detail="La latitud debe estar entre -90 y 90."
        )

    if longitud is not None and not -180 <= longitud <= 180:
        raise HTTPException(
            status_code=400,
            detail="La longitud debe estar entre -180 y 180."
        )

    if precision is not None and precision < 0:
        raise HTTPException(
            status_code=400,
            detail="La precisión no puede ser negativa."
        )

    # ------------------------------------------------------
    # 4. Construir ubicación
    # ------------------------------------------------------
    if latitud is not None and longitud is not None:
        ubicacion = (
            f"Latitud: {latitud}, "
            f"Longitud: {longitud}"
        )

        if precision is not None:
            ubicacion += f", Precisión: {precision} metros"
    else:
        ubicacion = "Ubicación no especificada"

    # ------------------------------------------------------
    # 5. Guardar imagen
    # ------------------------------------------------------
    os.makedirs("uploads", exist_ok=True)

    if file.content_type == "image/png":
        extension = ".png"
    elif file.content_type in ("image/jpeg", "image/jpg"):
        extension = ".jpg"
    else:
        extension = ".img"

    nombre_archivo = (
        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        f"{extension}"
    )

    ruta_archivo = os.path.join("uploads", nombre_archivo)

    try:
        with open(ruta_archivo, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        await file.close()

    # ------------------------------------------------------
    # 6. Detectar baches con YOLO
    # ------------------------------------------------------
    try:
        results = model.predict(
            source=ruta_archivo,
            save=False,
            conf=0.25
        )

        clases = results[0].names
        detecciones = results[0].boxes.cls.tolist()

    except Exception as e:
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)

        print("ERROR durante la detección YOLO:", str(e))

        raise HTTPException(
            status_code=500,
            detail="No fue posible analizar la imagen."
        )

    fecha_hora = datetime.now()

    # ------------------------------------------------------
    # 7. Preparar resultado de detección
    # ------------------------------------------------------
    if not detecciones:
        tipo_bache = "No detectado"

        asunto = "Reporte: Sin baches detectados"

        cuerpo = (
            f"Fecha y hora: {fecha_hora}\n"
            f"Ubicación: {ubicacion}\n"
            "No se detectaron baches."
        )

    else:
        tipos_detectados = [
            clases[int(indice)]
            for indice in detecciones
        ]

        tipo_bache = ", ".join(tipos_detectados)

        asunto = "Reporte: Bache detectado"

        cuerpo = (
            f"Fecha y hora: {fecha_hora}\n"
            f"Ubicación: {ubicacion}\n"
            f"Tipos detectados: {tipo_bache}"
        )

    # ------------------------------------------------------
    # 8. Guardar reporte en la base de datos
    # ------------------------------------------------------
    nuevo_reporte = Reporte(
        usuario_id=current_user.id,
        tipo=tipo_bache,
        fecha=fecha_hora,
        ubicacion=ubicacion,
        imagen=nombre_archivo
    )

    try:
        db.add(nuevo_reporte)
        db.commit()
        db.refresh(nuevo_reporte)

    except Exception as e:
        db.rollback()

        print("ERROR al guardar el reporte:", str(e))

        raise HTTPException(
            status_code=500,
            detail="No fue posible guardar el reporte en la base de datos."
        )

    # ------------------------------------------------------
    # 9. Enviar correo
    # ------------------------------------------------------
    try:
        await enviar_reporte_asincrono(
            asunto,
            cuerpo,
            adjunto_path=ruta_archivo
        )

    except Exception as e:
        # El reporte ya está guardado aunque falle el correo.
        print("ERROR al enviar correo:", str(e))

    # ------------------------------------------------------
    # 10. Responder al frontend
    # ------------------------------------------------------
    return {
        "tipo": tipo_bache,
        "fecha_hora": fecha_hora.strftime("%Y-%m-%d %H:%M:%S"),
        "ubicacion": ubicacion,
        "latitud": latitud,
        "longitud": longitud,
        "precision": precision,
        "usuario": current_user.email
    }


# ==========================================================
# Envío de correos
# ==========================================================
async def enviar_reporte_asincrono(
    asunto,
    cuerpo,
    adjunto_path=None
):
    mensaje = EmailMessage()

    mensaje["From"] = EMAIL_USER
    mensaje["To"] = "appbaches@gmail.com"
    mensaje["Subject"] = asunto

    mensaje.set_content(cuerpo)

    if adjunto_path:
        with open(adjunto_path, "rb") as archivo:
            contenido = archivo.read()

        if adjunto_path.lower().endswith(".png"):
            subtipo = "png"
        else:
            subtipo = "jpeg"

        mensaje.add_attachment(
            contenido,
            maintype="image",
            subtype=subtipo,
            filename=os.path.basename(adjunto_path)
        )

    await aiosmtplib.send(
        mensaje,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username=EMAIL_USER,
        password=EMAIL_PASS
    )


# ==========================================================
# Página 404 personalizada
# ==========================================================
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse(
        "404.html",
        {"request": request},
        status_code=404
    )


# ==========================================================
# Ejecución local
# ==========================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )