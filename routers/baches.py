from fastapi import APIRouter

router = APIRouter(prefix="/baches", tags=["Baches"])

@router.get("/")
def listar_baches():
    return {"mensaje": "Lista de baches"}
