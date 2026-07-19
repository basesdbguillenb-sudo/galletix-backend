import os
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
import uuid

# 1. Configuración de Supabase (se lee desde las Environment Variables de Vercel)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Inicialización de la aplicación FastAPI
app = FastAPI(title="Galletix POS API")

# Habilitar CORS para que el Frontend (HTML/JS) pueda comunicarse con esta API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción cambiaremos esto por la URL de tu Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Modelos de datos
class Producto(BaseModel):
    nombre: str
    descripcion: str
    precio: float
    stock: int

class LoginData(BaseModel):
    email: str
    password: str

class RegistroData(BaseModel):
    email: str
    password: str
    nombre: str
    rol: str

# --- Utilidad: exige que quien llama sea ADMIN ---
def verificar_admin(x_usuario_id: str = Header(..., alias="X-Usuario-Id")) -> str:
    """
    Se usa como dependencia en rutas que solo debe poder usar el dueño/admin.
    El frontend manda el ID del usuario logueado en el header X-Usuario-Id,
    y acá se confirma que ese usuario tenga rol ADMIN en la tabla 'profiles'.
    """
    try:
        perfil = supabase.table("profiles").select("rol").eq("id", x_usuario_id).single().execute()
    except Exception:
        raise HTTPException(status_code=403, detail="No autorizado.")

    if not perfil.data or perfil.data.get("rol") != "ADMIN":
        raise HTTPException(status_code=403, detail="Acceso solo para administradores.")

    return x_usuario_id

# --- RUTAS DE LA API ---

@app.get("/")
def leer_raiz():
    return {"mensaje": "Bienvenido a la API del POS de Galletix"}

@app.post("/login")
def iniciar_sesion(datos: LoginData):
    """Verifica las credenciales del usuario con Supabase y devuelve su nombre y rol."""
    try:
        respuesta = supabase.auth.sign_in_with_password({
            "email": datos.email,
            "password": datos.password
        })
        usuario_id = respuesta.user.id

        perfil = supabase.table("profiles").select("nombre, rol").eq("id", usuario_id).single().execute()

        return {
            "mensaje": "Inicio de sesión exitoso",
            "usuario_id": usuario_id,
            "nombre": perfil.data["nombre"] if perfil.data else "",
            "rol": perfil.data["rol"] if perfil.data else "EMPLEADO"
        }
    except Exception as e:
        print(f"Error de login: {e}")
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")

@app.post("/registro")
def registrar_usuario(datos: RegistroData, admin_id: str = Depends(verificar_admin)):
    """Registra un nuevo usuario. Solo un ADMIN puede crear usuarios nuevos."""
    try:
        respuesta_auth = supabase.auth.sign_up({
            "email": datos.email,
            "password": datos.password
        })

        usuario_id = respuesta_auth.user.id

        nuevo_perfil = {
            "id": usuario_id,
            "nombre": datos.nombre,
            "rol": datos.rol  # Debe ser 'ADMIN' o 'EMPLEADO'
        }
        supabase.table("profiles").insert(nuevo_perfil).execute()

        return {
            "mensaje": "Usuario creado exitosamente",
            "usuario_id": usuario_id
        }

    except Exception as e:
        print(f"Error en registro: {e}")
        raise HTTPException(status_code=400, detail=f"No se pudo registrar el usuario: {str(e)}")

@app.get("/usuarios")
def obtener_usuarios(admin_id: str = Depends(verificar_admin)):
    """Lista todos los usuarios del sistema (nombre y rol). Solo ADMIN."""
    try:
        respuesta = supabase.table("profiles").select("id, nombre, rol").execute()
        return respuesta.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Módulo de Productos ---

@app.get("/productos")
def obtener_productos():
    """Obtiene la lista de todos los productos activos."""
    respuesta = supabase.table("productos").select("*").eq("activo", True).execute()
    return respuesta.data

@app.post("/productos")
def crear_producto(producto: Producto):
    """Crea un nuevo producto en el inventario y maneja errores."""
    try:
        nuevo_producto = {
            "nombre": producto.nombre,
            "descripcion": producto.descripcion,
            "precio": producto.precio,
            "stock": producto.stock,
            "activo": True
        }
        respuesta = supabase.table("productos").insert(nuevo_producto).execute()
        return {"mensaje": "Producto creado con éxito", "datos": respuesta.data}
    except Exception as e:
        print("\n>>> ERROR DETALLADO AL GUARDAR EL PRODUCTO:")
        print(str(e))
        print(">>> --------------------------------------\n")
        raise HTTPException(status_code=400, detail=f"Falla en la base de datos: {str(e)}")

# --- Módulo de Ventas y Comprobantes ---

@app.post("/ventas")
async def registrar_venta(
    empleado_id: str = Form(...),
    total: float = Form(...),
    metodo_pago: str = Form(...),
    comprobante: UploadFile = File(None)
):
    try:
        comprobante_url = None

        if metodo_pago not in ["EFECTIVO", "TRANSFERENCIA"]:
            raise HTTPException(status_code=400, detail="Método de pago no válido.")

        if metodo_pago == "TRANSFERENCIA":
            if not comprobante:
                raise HTTPException(status_code=400, detail="Debe adjuntar comprobante.")

            extension = comprobante.filename.split(".")[-1]
            nombre_archivo = f"{uuid.uuid4()}.{extension}"
            contenido_archivo = await comprobante.read()
            supabase.storage.from_("comprobantes").upload(
                path=nombre_archivo,
                file=contenido_archivo,
                file_options={"content-type": comprobante.content_type}
            )
            comprobante_url = supabase.storage.from_("comprobantes").get_public_url(nombre_archivo)

        nueva_venta = {
            "empleado_id": empleado_id,
            "total": total,
            "metodo_pago": metodo_pago,
            "comprobante_url": comprobante_url
        }

        respuesta_db = supabase.table("ventas").insert(nueva_venta).execute()
        return {"mensaje": "Venta registrada exitosamente", "venta": respuesta_db.data}

    except Exception as e:
        print(f">>> ERROR EN VENTAS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ventas")
def obtener_ventas(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    admin_id: str = Depends(verificar_admin)
):
    """
    Historial de ventas para el panel de administración.
    - Filtrable por rango de fechas con ?fecha_inicio=...&fecha_fin=...
    - Incluye el nombre del empleado que hizo cada venta.
    - Solo accesible para usuarios con rol ADMIN.
    """
    try:
        query = supabase.table("ventas").select("*").order("fecha", desc=True)

        if fecha_inicio:
            query = query.gte("fecha", fecha_inicio)
        if fecha_fin:
            query = query.lte("fecha", fecha_fin)

        ventas = query.execute().data

        # Traemos los nombres de los empleados para no depender de una relación
        # configurada en la base de datos, y los "pegamos" a cada venta.
        perfiles = supabase.table("profiles").select("id, nombre").execute().data
        mapa_nombres = {p["id"]: p["nombre"] for p in perfiles}

        for venta in ventas:
            venta["empleado_nombre"] = mapa_nombres.get(venta["empleado_id"], "Desconocido")

        return ventas
    except Exception as e:
        print(f">>> ERROR AL OBTENER VENTAS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))