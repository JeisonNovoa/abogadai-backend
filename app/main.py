from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.database import engine, Base
from app.routes import auth, livekit, casos, referencias, sesiones, mensajes, perfil, migrations, usuarios, admin
import logging
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Abogadai API",
    description="API para la plataforma Abogadai - Generación de tutelas y derechos de petición con IA",
    version="2.0.0"
)

# Configurar CORS
# Permitir frontend de producción y desarrollo
allowed_origins = [
    settings.FRONTEND_URL,  # De .env (localhost en dev)
    "https://abogadai-frontend.onrender.com",  # Producción
    "http://localhost:5173",  # Desarrollo local
    "http://localhost:3000",  # Desarrollo alternativo
]

# Remover duplicados
allowed_origins = list(set(allowed_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Manejador global de excepciones para asegurar headers CORS en errores
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Manejador de excepciones HTTP que asegura headers CORS"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Manejador de errores de validación que asegura headers CORS"""
    logger.error(f"Validation Error: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejador global de excepciones que asegura headers CORS en errores 500"""
    logger.error(f"Unhandled Exception: {type(exc).__name__} - {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Incluir routers
app.include_router(auth.router)
app.include_router(livekit.router)
app.include_router(casos.router)
app.include_router(referencias.router)
app.include_router(sesiones.router)
app.include_router(mensajes.router)
app.include_router(perfil.router, prefix="/api")
app.include_router(migrations.router)  # Endpoint temporal para migraciones
app.include_router(usuarios.router)  # NUEVO - Endpoints de niveles y beneficios
app.include_router(admin.router)  # NUEVO - Endpoints de administración

# Configurar carpeta de archivos estáticos para evidencias de reembolso
uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
    logger.info(f"📁 Carpeta de uploads creada: {uploads_dir}")

app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
logger.info(f"📁 Archivos estáticos montados en /uploads desde {os.path.abspath(uploads_dir)}")


@app.get("/")
def read_root():
    return {
        "message": "Bienvenido a Abogadai API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
