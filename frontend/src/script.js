document.addEventListener("DOMContentLoaded", function () {
    // LOGIN
    const loginButton = document.getElementById("loginButton");

    if (loginButton) {
        loginButton.addEventListener("click", function () {
            const username = document.getElementById("username").value.trim();
            const password = document.getElementById("password").value.trim();

            if (username === "" || password === "") {
                alert("Por favor, completa todos los campos.");
                return;
            }

            fetch('http://localhost:5000/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.message === "Inicio de sesión exitoso") {
                        localStorage.setItem('currentUser', data.user.username);
                        alert("Inicio de sesión exitoso. Redirigiendo...");
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

    // REGISTRO
    const registroButton = document.getElementById("registroButton");

    if (registroButton) {
        registroButton.addEventListener("click", function () {
            window.location.href = "registro.html";
        });
    }

    const returnButton = document.getElementById("returnButton");
    if (returnButton) {
        returnButton.addEventListener("click", function () {
            window.location.href = "login.html";
        });
    }

    const confirmButton = document.getElementById("confirmButton");

    if (confirmButton) {
        confirmButton.addEventListener("click", function () {
            const username = document.getElementById("username").value.trim();
            const password = document.getElementById("password").value.trim();
            const confirmPassword = document.getElementById("confirm-password").value.trim();

            if (username === "" || password === "" || confirmPassword === "") {
                alert("Por favor, completa todos los campos.");
                return;
            }

            if (password !== confirmPassword) {
                alert("Las contraseñas no coinciden.");
                return;
            }

            fetch('http://localhost:5000/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.message === "Usuario registrado exitosamente") {
                        alert("Registro exitoso. Redirigiendo al login...");
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

    // MOSTRAR USUARIO ACTUAL
    const userDisplay = document.querySelector(".user-display");

    if (userDisplay) {
        const currentUser = localStorage.getItem('currentUser');
        if (currentUser) {
            userDisplay.value = "@" + currentUser;
        } else {
            window.location.href = "login.html";
        }
    }

    // MOSTRAR SALDO
    const saldoElemento = document.querySelector(".saldo-valor");

    if (saldoElemento) {
        let saldoActual = localStorage.getItem("saldoDisponible");

        if (!saldoActual) {
            saldoActual = 500; // valor por defecto
            localStorage.setItem("saldoDisponible", saldoActual);
        }

        saldoElemento.textContent = `${parseFloat(saldoActual).toFixed(2)} €`;
    }

    // REPARTO ALEATORIO DE SALDO EN 3 BURBUJAS
    function repartirSaldoAleatoriamente(total) {
        const parte1 = Math.random();
        const parte2 = Math.random();
        const parte3 = Math.random();
        const suma = parte1 + parte2 + parte3;

        const ingreso = Math.round((parte1 / suma) * total);
        const gasto = Math.round((parte2 / suma) * total);
        let inversion = total - ingreso - gasto; // ajustamos para que sume exacto

        return [ingreso, gasto, inversion];
    }

    const burbujas = document.querySelectorAll(".bubble");

    if (burbujas.length === 3 && saldoElemento) {
        const saldoTotal = parseFloat(localStorage.getItem("saldoDisponible")) || 0;

        const [ingresos, gastos, inversiones] = repartirSaldoAleatoriamente(saldoTotal);
        const cantidades = [ingresos, gastos, inversiones];
        const max = Math.max(...cantidades);
        const minSize = 60;
        const maxSize = 100;

        burbujas.forEach((bubble, i) => {
            const valorEl = bubble.querySelector(".valor");
            const labelEl = bubble.querySelector(".label");

            valorEl.textContent = cantidades[i];
            bubble.setAttribute("data-value", cantidades[i]);

            const size = minSize + ((cantidades[i] / max) * (maxSize - minSize));
            bubble.style.width = `${size}px`;
            bubble.style.height = `${size}px`;
            bubble.style.fontSize = `${Math.max(12, size / 5)}px`;
            bubble.style.lineHeight = `${size}px`;
            bubble.style.transition = "all 0.3s ease";
        });
    }
});
