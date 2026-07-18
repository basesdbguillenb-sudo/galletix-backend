const API_URL = "http://localhost:8000";

const formProducto = document.getElementById("form-producto");
const tablaVentas = document.getElementById("tabla-ventas");

// 1. Lógica para crear un nuevo producto
formProducto.addEventListener("submit", async (e) => {
    e.preventDefault();

    const nuevoProducto = {
        nombre: document.getElementById("prod-nombre").value,
        descripcion: document.getElementById("prod-desc").value,
        precio: parseFloat(document.getElementById("prod-precio").value),
        stock: parseInt(document.getElementById("prod-stock").value)
    };

    try {
        const respuesta = await fetch(`${API_URL}/productos`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(nuevoProducto)
        });

        if (respuesta.ok) {
            alert("Producto agregado con éxito");
            formProducto.reset(); // Limpiar el formulario
        } else {
            alert("Error al agregar el producto");
        }
    } catch (error) {
        console.error("Error:", error);
        alert("Error de conexión con el servidor.");
    }
});

// 2. Lógica para cargar el historial de ventas
async function cargarVentas() {
    try {
        const respuesta = await fetch(`${API_URL}/ventas`);
        const ventas = await respuesta.json();

        tablaVentas.innerHTML = ""; // Limpiar tabla

        ventas.forEach(venta => {
            // Formatear la fecha
            const fecha = new Date(venta.fecha).toLocaleString();
            
            // Lógica para el botón del comprobante
            let botonComprobante = "-";
            if (venta.metodo_pago === "TRANSFERENCIA" && venta.comprobante_url) {
                botonComprobante = `<a href="${venta.comprobante_url}" target="_blank" style="color: blue; text-decoration: underline;">Ver Foto</a>`;
            }

            const fila = document.createElement("tr");
            fila.innerHTML = `
                <td style="padding: 10px; border-bottom: 1px solid #eee;">${venta.id}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">${fecha}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">$${venta.total.toFixed(2)}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">${venta.metodo_pago}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">${botonComprobante}</td>
            `;
            tablaVentas.appendChild(fila);
        });
    } catch (error) {
        console.error("Error al cargar ventas:", error);
        tablaVentas.innerHTML = "<tr><td colspan='5'>Error al cargar las ventas.</td></tr>";
    }
}

// Cargar las ventas al abrir la página
cargarVentas();