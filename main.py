# Actualización para forzar un despliegue nuevo en Vercel
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# ... (el resto de tu código hacia abajo se queda exactamente igual)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
import uuid

# 1. Configuración de Supabase
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
import uuid

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Inicialización de la aplicación FastAPI
app = FastAPI(title="Galletix POS API")

# Habilitar CORS para que el Frontend (HTML/JS) pueda comunicarse con esta API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción cambiaremos esto por la URL de tu Vercel
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

# --- RUTAS DE LA API ---

@app.get("/")
def leer_raiz():
    return {"mensaje": "Bienvenido a la API del POS de Galletix"}

class LoginData(BaseModel):
    email: str
    password: str

@app.post("/login")
def iniciar_sesion(datos: LoginData):
    """Verifica las credenciales del usuario con Supabase."""
    try:
        # Intentamos iniciar sesión usando el cliente de Supabase
        respuesta = supabase.auth.sign_in_with_password({
            "email": datos.email,
            "password": datos.password
        })
        
        # Si tiene éxito, extraemos el ID del usuario y su rol
        return {
            "mensaje": "Inicio de sesión exitoso", 
            "usuario_id": respuesta.user.id
        }
    except Exception as e:
        print(f"Error de login: {e}")
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")

# Modelo de datos para el registro
class RegistroData(BaseModel):
    email: str
    password: str
    nombre: str
    rol: str

@app.post("/registro")
def registrar_usuario(datos: RegistroData):
    """Registra un nuevo usuario en Supabase y crea su perfil en la base de datos."""
    try:
        # 1. Crear el usuario en el sistema de Autenticación de Supabase
        respuesta_auth = supabase.auth.sign_up({
            "email": datos.email,
            "password": datos.password
        })
        
        usuario_id = respuesta_auth.user.id
        
        # 2. Guardar los detalles del empleado en nuestra tabla 'profiles'
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
        # 1. Preparamos el diccionario con los datos del producto
        nuevo_producto = {
            "nombre": producto.nombre,
            "descripcion": producto.descripcion,
            "precio": producto.precio,
            "stock": producto.stock,
            "activo": True
        }
        
        # 2. Intentamos insertar el registro en Supabase
        respuesta = supabase.table("productos").insert(nuevo_producto).execute()
        return {"mensaje": "Producto creado con éxito", "datos": respuesta.data}
        
    except Exception as e:
        # 3. Si algo falla, atrapamos la excepción y la imprimimos en la terminal
        print("\n>>> ERROR DETALLADO AL GUARDAR EL PRODUCTO:")
        print(str(e))
        print(">>> --------------------------------------\n")
        
        # Devolvemos el error de forma segura al frontend
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
def obtener_ventas():
    """Obtiene el historial de ventas para el panel de administración, ordenado por fecha."""
    try:
        respuesta = supabase.table("ventas").select("*").order("fecha", desc=True).execute()
        return respuesta.data
    except Exception as e:
        print(f">>> ERROR AL OBTENER VENTAS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))