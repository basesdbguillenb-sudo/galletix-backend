const API_URL = "http://localhost:8000";
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
            // Guardamos el ID real del empleado en el navegador
            localStorage.setItem("empleado_id", resultado.usuario_id);
            
            // Redirigimos al panel del cajero
            window.location.href = "index.html";
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