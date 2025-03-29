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
                        <th>Acciones</th>
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
                            <td>
                                <button class="ver-detalle-btn" data-simbolo="${etf.symbol}">
                                    Ver Detalle
                                </button>
                            </td>
                        `;
                        tabla.appendChild(fila);
                    });
                    
                    etfListElement.appendChild(tabla);
                    
                    // Añadir event listeners a los botones de ver detalle
                    document.querySelectorAll('.ver-detalle-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const simbolo = this.getAttribute('data-simbolo');
                            verDetalleETF(simbolo);
                        });
                    });
                } else {
                    etfListElement.innerHTML = '<p>No se encontraron ETFs disponibles.</p>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                etfListElement.innerHTML = '<p>Error al cargar los ETFs. Por favor, inténtalo de nuevo más tarde.</p>';
            });
    }
    
    // Función para ver detalle de un ETF específico
    function verDetalleETF(simbolo) {
        const detalleElement = document.getElementById('etf-detalle');
        if (!detalleElement) return;
        
        detalleElement.innerHTML = '<p>Cargando datos del ETF...</p>';
        
        fetch(`http://localhost:5000/api/etf/${simbolo}/precios`)
            .then(response => response.json())
            .then(data => {
                // Construir la vista detallada del ETF
                let contenidoHTML = `
                    <h2>${data.etf.name} (${data.etf.symbol})</h2>
                    
                    <div class="etf-info-principal">
                        <div class="precio-principal">
                            <span class="etiqueta">Precio Actual:</span>
                            <span class="valor">$${data.etf.current_price ? data.etf.current_price.toFixed(2) : 'N/A'}</span>
                        </div>
                        
                        <div class="volumen-principal">
                            <span class="etiqueta">Volumen:</span>
                            <span class="valor">${data.etf.current_volume ? data.etf.current_volume.toLocaleString() : 'N/A'}</span>
                        </div>
                    </div>
                    
                    <div class="etf-descripcion">
                        <h3>Descripción</h3>
                        <p>${data.etf.description || 'No hay descripción disponible.'}</p>
                    </div>
                    
                    <div class="etf-estadisticas">
                        <h3>Estadísticas</h3>
                        <ul>
                            <li><strong>Precio Promedio:</strong> $${data.estadisticas.precio_promedio ? data.estadisticas.precio_promedio.toFixed(2) : 'N/A'}</li>
                            <li><strong>Precio Máximo:</strong> $${data.estadisticas.precio_max ? data.estadisticas.precio_max.toFixed(2) : 'N/A'}</li>
                            <li><strong>Precio Mínimo:</strong> $${data.estadisticas.precio_min ? data.estadisticas.precio_min.toFixed(2) : 'N/A'}</li>
                            <li><strong>Volumen Promedio:</strong> ${data.estadisticas.volumen_promedio ? Math.round(data.estadisticas.volumen_promedio).toLocaleString() : 'N/A'}</li>
                        </ul>
                    </div>
                `;
                
                // Añadir tabla de histórico de precios si hay datos
                if (data.historico && data.historico.length > 0) {
                    contenidoHTML += `
                        <div class="etf-historico">
                            <h3>Histórico de Precios</h3>
                            <table class="tabla-historico">
                                <tr>
                                    <th>Fecha</th>
                                    <th>Apertura</th>
                                    <th>Máximo</th>
                                    <th>Mínimo</th>
                                    <th>Cierre</th>
                                    <th>Volumen</th>
                                </tr>
                    `;
                    
                    // Mostrar los últimos 10 registros para no saturar
                    const registrosAMostrar = data.historico.slice(-10);
                    
                    registrosAMostrar.forEach(registro => {
                        // Formatear fecha a formato local
                        const fecha = new Date(registro.fecha).toLocaleDateString();
                        
                        contenidoHTML += `
                            <tr>
                                <td>${fecha}</td>
                                <td>$${registro.apertura ? registro.apertura.toFixed(2) : 'N/A'}</td>
                                <td>$${registro.maximo ? registro.maximo.toFixed(2) : 'N/A'}</td>
                                <td>$${registro.minimo ? registro.minimo.toFixed(2) : 'N/A'}</td>
                                <td>$${registro.cierre ? registro.cierre.toFixed(2) : 'N/A'}</td>
                                <td>${registro.volumen ? registro.volumen.toLocaleString() : 'N/A'}</td>
                            </tr>
                        `;
                    });
                    
                    contenidoHTML += `
                            </table>
                        </div>
                    `;
                }
                
                // Agregar botón para volver a la lista
                contenidoHTML += `
                    <div class="acciones-detalle">
                        <button class="volver-btn" onclick="document.getElementById('etf-list').style.display='block';document.getElementById('etf-detalle').style.display='none';">
                            Volver a la lista
                        </button>
                    </div>
                `;
                
                detalleElement.innerHTML = contenidoHTML;
                
                // Mostrar la sección de detalle y ocultar la lista
                document.getElementById('etf-list').style.display = 'none';
                detalleElement.style.display = 'block';
            })
            .catch(error => {
                console.error('Error:', error);
                detalleElement.innerHTML = `<p>Error al cargar los datos del ETF ${simbolo}. Por favor, inténtalo de nuevo más tarde.</p>
                <button onclick="document.getElementById('etf-list').style.display='block';document.getElementById('etf-detalle').style.display='none';">
                    Volver a la lista
                </button>`;
            });
    }
    
    // Inicializar carga de ETFs si estamos en la página de cartera
    if (document.getElementById('etf-list')) {
        cargarListaETFs();
    }
});