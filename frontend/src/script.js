document.addEventListener("DOMContentLoaded", function () {
    // Capturar el botón de inicio de sesión
    const loginButton = document.getElementById("loginButton");
    
    if (loginButton) {
        loginButton.addEventListener("click", function () {
            // Obtener los valores de los campos
            const username = document.getElementById("username").value.trim();
            const password = document.getElementById("password").value.trim();
            
            // Validar que los campos no estén vacíos
            if (username === "" || password === "") {
                alert("Por favor, completa todos los campos.");
                return;
            }

            // Realizar la petición de login al backend
            fetch('http://localhost:5000/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.message === "Inicio de sesión exitoso") {
                    // Guardar el nombre de usuario en localStorage
                    localStorage.setItem('currentUser', data.user.username);
                    
                    alert("Inicio de sesión exitoso. Redirigiendo...");
                    // Redirigir a cartera.html
                    window.location.href = "cartera.html";
                } else {
                    alert(data.error || "Error al iniciar sesión");
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert("Error de conexión con el servidor");
            });
        });
    }

    // Capturar el botón de registro en la página de inicio
    const registroButton = document.getElementById("registroButton");
    
    if (registroButton) {
        registroButton.addEventListener("click", function () {
            // Redirigir al registro
            window.location.href = "registro.html";
        });
    }

    // Capturar el botón de Confirmar en la página de registro
    const confirmButton = document.getElementById("confirmButton");

    if (confirmButton) {
        confirmButton.addEventListener("click", function () {
            // Obtener valores del formulario
            const username = document.getElementById("username").value.trim();
            const password = document.getElementById("password").value.trim();
            const confirmPassword = document.getElementById("confirm-password").value.trim();
            
            // Validar que los campos no estén vacíos
            if (username === "" || password === "" || confirmPassword === "") {
                alert("Por favor, completa todos los campos.");
                return;
            }
            
            // Validar que las contraseñas coincidan
            if (password !== confirmPassword) {
                alert("Las contraseñas no coinciden.");
                return;
            }
            
            // Realizar la petición de registro al backend
            fetch('http://localhost:5000/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.message === "Usuario registrado exitosamente") {
                    alert("Registro exitoso. Redirigiendo al login...");
                    // Redirigir al login
                    window.location.href = "login.html";
                } else {
                    alert(data.error || "Error en el registro");
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert("Error de conexión con el servidor");
            });
        });
    }
    
    // Cargar el nombre de usuario en la página de cartera
    const userDisplay = document.querySelector(".user-display");
    if (userDisplay) {
        const currentUser = localStorage.getItem('currentUser');
        if (currentUser) {
            userDisplay.value = "@" + currentUser;
        } else {
            // Si no hay usuario conectado, redirigir al login
            window.location.href = "login.html";
        }
    }
});