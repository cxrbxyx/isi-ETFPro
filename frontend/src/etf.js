document.addEventListener("DOMContentLoaded", function() {
    // Función para cargar todos los ETFs disponibles
    function cargarListaETFs() {
        const etfListElement = document.getElementById('etf-list');
        if (!etfListElement) return;
        
        etfListElement.innerHTML = '<p>Cargando ETFs...</p>';
        
        fetch('http://localhost:5000/api/etfs')
            .then(response => response.json())
            .then(data => {
                if (data.etfs && data.etfs.length > 0) {
                    etfListElement.innerHTML = '';
                    const tabla = document.createElement('table');
                    tabla.className = 'etf-table';
                    
                    // Crear encabezados
                    const encabezado = document.createElement('tr');
                    encabezado.innerHTML = `
                        <th>Símbolo</th>
                        <th>Nombre</th>
                        <th>Precio Actual</th>
                        <th>Volumen</th>
                    `;
                    tabla.appendChild(encabezado);
                    
                    // Añadir filas
                    data.etfs.forEach(etf => {
                        const fila = document.createElement('tr');
                        fila.innerHTML = `
                            <td>${etf.symbol}</td>
                            <td>${etf.name}</td>
                            <td>${etf.current_price ? '$' + etf.current_price.toFixed(2) : 'N/A'}</td>
                            <td>${etf.current_volume ? etf.current_volume.toLocaleString() : 'N/A'}</td>
                        `;
                        tabla.appendChild(fila);
                    });
                    
                    etfListElement.appendChild(tabla);
                } else {
                    etfListElement.innerHTML = '<p>No se encontraron ETFs disponibles.</p>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                etfListElement.innerHTML = '<p>Error al cargar los ETFs. Por favor, inténtalo de nuevo más tarde.</p>';
            });
    }
    
    // Inicializar carga de ETFs si estamos en la página de cartera
    if (document.getElementById('etf-list')) {
        cargarListaETFs();
    }
});