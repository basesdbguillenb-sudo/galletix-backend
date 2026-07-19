// La URL donde está corriendo tu servidor de Python (FastAPI)
const API_URL = "https://galletix-backend.vercel.app";

// Variables globales para manejar el estado
let carrito = [];
let totalOrden = 0;

// Referencias a los elementos del HTML
const gridProductos = document.getElementById("grid-productos");
const listaCarrito = document.getElementById("lista-carrito");
const textoTotal = document.getElementById("total-orden");
const selectMetodoPago = document.getElementById("metodo-pago");
const contenedorComprobante = document.getElementById("contenedor-comprobante");
const fotoComprobante = document.getElementById("foto-comprobante");
const formularioPago = document.getElementById("formulario-pago");

// 1. Mostrar/Ocultar campo de comprobante según el método de pago
selectMetodoPago.addEventListener("change", (e) => {
    if (e.target.value === "TRANSFERENCIA") {
        contenedorComprobante.style.display = "block";
        fotoComprobante.required = true;
    } else {
        contenedorComprobante.style.display = "none";
        fotoComprobante.required = false;
        fotoComprobante.value = ""; // Limpiar el archivo si cambian a efectivo
    }
});

// 2. Cargar los productos desde la API de Python
async function cargarProductos() {
    try {
        const respuesta = await fetch(`${API_URL}/productos`);
        const productos = await respuesta.json();
        
        gridProductos.innerHTML = ""; // Limpiar el mensaje de "Cargando..."
        
        productos.forEach(producto => {
            const tarjeta = document.createElement("div");
            tarjeta.className = "tarjeta-producto";
            tarjeta.innerHTML = `
                <h3>${producto.nombre}</h3>
                <p>$${producto.precio.toFixed(2)}</p>
            `;
            // Al hacer clic, se agrega al carrito
            tarjeta.addEventListener("click", () => agregarAlCarrito(producto));
            gridProductos.appendChild(tarjeta);
        });
    } catch (error) {
        console.error("Error al cargar productos:", error);
        gridProductos.innerHTML = "<p>Error al cargar los productos. Asegúrate de que el servidor Python esté encendido.</p>";
    }
}

// 3. Lógica para agregar al carrito
function agregarAlCarrito(producto) {
    carrito.push(producto);
    totalOrden += producto.precio;
    actualizarVistaCarrito();
}

// 4. Actualizar la lista visual del carrito
function actualizarVistaCarrito() {
    listaCarrito.innerHTML = "";
    carrito.forEach((producto, index) => {
        const li = document.createElement("li");
        li.innerHTML = `
            <span>${producto.nombre}</span>
            <span>$${producto.precio.toFixed(2)}</span>
        `;
        listaCarrito.appendChild(li);
    });
    textoTotal.innerText = totalOrden.toFixed(2);
}

// 5. Enviar la venta al Backend
formularioPago.addEventListener("submit", async (e) => {
    e.preventDefault(); // Evitar que la página se recargue

    if (carrito.length === 0) {
        alert("El carrito está vacío. Agrega productos primero.");
        return;
    }

    // Usamos FormData porque vamos a enviar texto Y un archivo de imagen al mismo tiempo
    const formData = new FormData();
    
    // Obtenemos el ID real del empleado que inició sesión
    const empleadoId = localStorage.getItem("empleado_id");
    
    if (!empleadoId) {
        alert("Error: No has iniciado sesión.");
        window.location.href = "login.html";
        return;
    }
    
    // Adjuntamos los datos a la petición
    formData.append("empleado_id", empleadoId); 
    formData.append("total", totalOrden);
    formData.append("metodo_pago", selectMetodoPago.value);

    // Si es transferencia, adjuntamos la imagen
    if (selectMetodoPago.value === "TRANSFERENCIA") {
        formData.append("comprobante", fotoComprobante.files[0]);
    }

    try {
        const respuesta = await fetch(`${API_URL}/ventas`, {
            method: "POST",
            body: formData
        });

        const resultado = await respuesta.json();

        if (respuesta.ok) {
            alert("¡Venta registrada con éxito!");
            // Limpiar la interfaz para el siguiente cliente
            carrito = [];
            totalOrden = 0;
            actualizarVistaCarrito();
            selectMetodoPago.value = "EFECTIVO";
            contenedorComprobante.style.display = "none";
            fotoComprobante.value = "";
        } else {
            alert(`Error al registrar la venta: ${resultado.detail}`);
        }
    } catch (error) {
        console.error("Error al procesar el pago:", error);
        alert("Error de conexión con el servidor.");
    }
});

// Arrancar la aplicación pidiendo los productos
cargarProductos();