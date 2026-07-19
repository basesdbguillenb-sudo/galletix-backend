const API_URL = "https://galletix-backend.vercel.app";
const formLogin = document.getElementById("form-login");
const mensajeError = document.getElementById("mensaje-error");

formLogin.addEventListener("submit", async (e) => {
    e.preventDefault(); // Evita que la página se recargue

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        const respuesta = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email, password })
        });

        const resultado = await respuesta.json();

        if (respuesta.ok) {
            // Guardamos la identidad del usuario logueado en el navegador
            localStorage.setItem("empleado_id", resultado.usuario_id);
            localStorage.setItem("nombre", resultado.nombre);
            localStorage.setItem("rol", resultado.rol);

            // Redirigimos según el rol: el dueño va al panel admin,
            // el resto de empleados va directo al punto de venta.
            if (resultado.rol === "ADMIN") {
                window.location.href = "admin.html";
            } else {
                window.location.href = "index.html";
            }
        } else {
            // Mostrar error visual si las credenciales fallan
            mensajeError.innerText = resultado.detail;
            mensajeError.style.display = "block";
        }
    } catch (error) {
        console.error("Error:", error);
        mensajeError.innerText = "Error de conexión con el servidor.";
        mensajeError.style.display = "block";
    }
});
