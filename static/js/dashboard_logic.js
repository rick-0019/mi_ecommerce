// --- MODO AGENTIC: Dashboard Logic Consolidation ---
let timerGeneral;
let tipoActual = '';
let selectedSucursalId = null;
let selectedSucursalNombre = null;

document.addEventListener("DOMContentLoaded", function () {
    // Helper para normalizar texto (quitar tildes y a minúsculas)
    const normalizeStr = (str) => {
        return str.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    };

    // 1. Buscador de Pedidos (Filtrado Local)
    if (buscadorPedidosLocales) {
        buscadorPedidosLocales.addEventListener('keyup', function () {
            let valor = normalizeStr(this.value);
            let filas = document.querySelectorAll('.fila-pedido');
            filas.forEach(fila => {
                let textoFila = normalizeStr(fila.innerText);
                fila.style.display = textoFila.includes(valor) ? '' : 'none';
            });
        });
    }

    // 2. Buscador Directo en Tabla de Catálogo (AJAX)
    if (buscadorProductosDirecto) {
        buscadorProductosDirecto.addEventListener('keyup', function () {
            ejecutarBusquedaGestionProductos(this.value);
        });
    }

    // 3. Listener para Buscador de Transferencias (Delegado por ser AJAX)
    document.addEventListener('keyup', function (e) {
        if (e.target && e.target.id === 'buscadorTransfDirecto') {
            ejecutarBusquedaTransf(e.target.value);
        }
    });

    // 4. Activar pestaña por URL o errores
    const urlParams = new URLSearchParams(window.location.search);
    const tieneErrores = document.querySelector('#formNuevoProductoCompleto .text-danger');
    if (urlParams.get('tab') === 'productos' || tieneErrores) {
        const productTab = document.getElementById('pills-productos-tab');
        if (productTab) {
            bootstrap.Tab.getOrCreateInstance(productTab).show();
            if (tieneErrores) {
                const collapse = document.getElementById('formNuevoProductoCompleto');
                if (collapse) bootstrap.Collapse.getOrCreateInstance(collapse).show();
            }
        }
    }

    // 4. Inicializar widgets AJAX
    if (typeof initSearchWidget === 'function') {
        initSearchWidget('categoria');
        initSearchWidget('marca');
    }

    // 5. Listener para Tab de Transferencias (Carga diferida)
    const triggerTabTransf = document.querySelector('#pills-transferencias-tab');
    if (triggerTabTransf) {
        triggerTabTransf.addEventListener('shown.bs.tab', function () {
            cargarTransferencias();
        });
    }
});

// --- FUNCIONES DE BÚSQUEDA ---

function ejecutarBusquedaTransf(query) {
    const resultadosDiv = document.getElementById('resultados-transferencia');
    if (!resultadosDiv) return;

    if (query.length < 3) {
        resultadosDiv.innerHTML = '<div class="text-center py-3 text-muted small">Escribí al menos 3 letras...</div>';
        return;
    }

    clearTimeout(timerGeneral);
    timerGeneral = setTimeout(() => {
        fetch(`/gestion/buscar-productos-transf/?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
                resultadosDiv.innerHTML = '';
                if (data.productos && data.productos.length > 0) {
                    data.productos.forEach(p => {
                        const sinStock = p.stock <= 0;
                        const item = document.createElement('div');
                        item.className = `list-group-item d-flex justify-content-between align-items-center animate__animated animate__fadeIn ${sinStock ? 'opacity-75 bg-light' : ''}`;
                        item.innerHTML = `
                            <div class="d-flex align-items-center">
                                <span class="badge bg-secondary me-3">${p.sku}</span>
                                <div>
                                    <div class="fw-bold ${sinStock ? 'text-muted' : ''}">${p.nombre}</div>
                                    <div class="text-muted small">Stock: <span class="badge ${sinStock ? 'bg-danger' : 'bg-success'}">${p.stock}</span> | ${p.precio}</div>
                                </div>
                            </div>
                            <button onclick="agregarAlCarritoTransf(${p.id})" 
                                    class="btn btn-sm ${sinStock ? 'btn-outline-secondary disabled' : 'btn-primary'} px-3 rounded-pill shadow-sm"
                                    ${sinStock ? 'disabled' : ''}>
                                <i class="bi bi-plus-lg me-1"></i>Agregar
                            </button>
                        `;
                        resultadosDiv.appendChild(item);
                    });
                } else {
                    resultadosDiv.innerHTML = '<div class="list-group-item text-danger text-center">Sin coincidencias o sin stock</div>';
                }
            })
            .catch(err => console.error("Error búsqueda transf:", err));
    }, 300);
}

function ejecutarBusquedaGestionProductos(query) {
    const contenedor = document.getElementById('cuerpo-tabla-gestion');
    if (!contenedor) {
        console.warn("No se encontró el contenedor 'cuerpo-tabla-gestion'");
        return;
    }

    clearTimeout(timerGeneral);
    timerGeneral = setTimeout(() => {
        console.log("Buscando productos:", query);
        fetch(`/gestion-productos/buscar-gestion-ajax/?q=${encodeURIComponent(query)}`)
            .then(res => res.text())
            .then(html => {
                contenedor.innerHTML = html;
            })
            .catch(err => console.error("Error búsqueda gestión:", err));
    }, 300);
}

// --- MODALES Y ACCIONES RÁPIDAS ---

function configurarModal(tipo) {
    tipoActual = tipo;
    const titulo = document.getElementById('tituloModalRapido');
    if (titulo) titulo.innerText = 'Nueva ' + (tipo === 'marca' ? 'Marca' : 'Categoría');
}

function guardarRapido() {
    const inputNombre = document.getElementById('nombreRapido');
    const nombre = inputNombre ? inputNombre.value.trim() : '';
    if (!nombre) return alert("Ingrese un nombre");

    fetch(`/gestion-productos/crear-rapido/${tipoActual}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
        body: JSON.stringify({ nombre: nombre })
    })
        .then(res => res.json())
        .then(data => {
            if (data.id) {
                const select = document.querySelector(`select[name="${tipoActual}"]`);
                if (select) select.add(new Option(data.nombre, data.id, true, true));
                if (typeof seleccionarItem === 'function') seleccionarItem(tipoActual, data.id, data.nombre);
                bootstrap.Modal.getInstance(document.getElementById('modalCrearRapido')).hide();
            }
        })
        .catch(err => console.error('Error guardar rápido:', err));
}

// --- WIDGETS DE BÚSQUEDA (CATEGORÍA/MARCA) ---

function initSearchWidget(tipo) {
    const input = document.getElementById(`${tipo}_search`);
    const resultsContainer = document.getElementById(`${tipo}_results`);
    const hiddenSelect = document.querySelector(`select[name="${tipo}"]`);
    const feedback = document.getElementById(`${tipo}_selected_text`);
    let timeoutWidget = null;

    if (!input || !hiddenSelect) return;

    if (hiddenSelect.value) {
        const sel = hiddenSelect.options[hiddenSelect.selectedIndex];
        if (sel && sel.value) {
            input.value = sel.text;
            feedback.style.display = 'block';
            feedback.innerText = `Seleccionado: ${sel.text}`;
        }
    }

    input.addEventListener('input', function () {
        clearTimeout(timeoutWidget);
        const query = this.value.trim();
        if (query.length < 2) {
            resultsContainer.style.display = 'none';
            return;
        }

        timeoutWidget = setTimeout(() => {
            fetch(`/gestion-productos/buscar-ajax/?tipo=${tipo}&q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    resultsContainer.innerHTML = '';
                    if (data.results && data.results.length > 0) {
                        data.results.forEach(item => {
                            const div = document.createElement('a');
                            div.className = 'list-group-item list-group-item-action cursor-pointer';
                            div.innerHTML = item.text;
                            div.onclick = () => seleccionarItem(tipo, item.id, item.text);
                            resultsContainer.appendChild(div);
                        });
                        resultsContainer.style.display = 'block';
                    } else {
                        resultsContainer.innerHTML = '<div class="list-group-item text-muted">Sin resultados</div>';
                        resultsContainer.style.display = 'block';
                    }
                })
                .catch(err => console.error("Error widget:", err));
        }, 300);
    });

    document.addEventListener('click', (e) => {
        if (input && !input.contains(e.target) && resultsContainer && !resultsContainer.contains(e.target)) {
            resultsContainer.style.display = 'none';
        }
    });
}

function seleccionarItem(tipo, id, texto) {
    const input = document.getElementById(`${tipo}_search`);
    const hiddenSelect = document.querySelector(`select[name="${tipo}"]`);
    const feedback = document.getElementById(`${tipo}_selected_text`);

    if (!input || !hiddenSelect) return;

    let opt = hiddenSelect.querySelector(`option[value="${id}"]`);
    if (!opt) {
        opt = new Option(texto, id, true, true);
        hiddenSelect.add(opt);
    }
    hiddenSelect.value = id;
    input.value = texto;
    if (feedback) {
        feedback.innerText = `Seleccionado: ${texto}`;
        feedback.style.display = 'block';
    }
    const results = document.getElementById(`${tipo}_results`);
    if (results) results.style.display = 'none';
}

function limpiarSeleccion(tipo) {
    const input = document.getElementById(`${tipo}_search`);
    const hiddenSelect = document.querySelector(`select[name="${tipo}"]`);
    const feedback = document.getElementById(`${tipo}_selected_text`);
    if (input) input.value = '';
    if (hiddenSelect) hiddenSelect.value = '';
    if (feedback) {
        feedback.style.display = 'none';
        feedback.innerText = '';
    }
}

// --- TRANSFERENCIAS LOGIC ---

function cargarTransferencias() {
    const contenedor = document.getElementById('contenedor-ajax-transferencias');
    if (!contenedor) return;
    if (contenedor.innerHTML.includes('row animate__animated')) return;

    fetch('/gestion/transferencias/')
        .then(res => res.text())
        .then(html => {
            contenedor.innerHTML = html;
            restaurarSeleccionSucursal();
        })
        .catch(err => {
            console.error("Error cargar panel:", err);
            contenedor.innerHTML = '<div class="alert alert-danger">Error al cargar panel de transferencias.</div>';
        });
}

function recargarPanelTransferencias() {
    const contenedor = document.getElementById('contenedor-ajax-transferencias');
    if (!contenedor) return;
    fetch('/gestion/transferencias/')
        .then(res => res.text())
        .then(html => {
            contenedor.innerHTML = html;
            restaurarSeleccionSucursal();
        })
        .catch(err => console.error('Error recargando panel:', err));
}

function recargarSoloRemito() {
    const contenedor = document.getElementById('contenedor-remito-ajax');
    if (!contenedor) return;
    fetch('/gestion/obtener-remito-ajax/')
        .then(res => res.text())
        .then(html => {
            contenedor.innerHTML = html;
        })
        .catch(err => console.error('Error recargando remito:', err));
}

function seleccionarDestino(id, nombre) {
    selectedSucursalId = id;
    selectedSucursalNombre = nombre;
    const input = document.getElementById('input-sucursal-id');
    const badge = document.getElementById('sucursal-seleccionada-badge');
    if (input) input.value = id;
    if (badge) {
        badge.innerText = "Destino: " + nombre;
        badge.style.display = 'block';
    }
}

function restaurarSeleccionSucursal() {
    if (selectedSucursalId) {
        const input = document.getElementById('input-sucursal-id');
        const badge = document.getElementById('sucursal-seleccionada-badge');
        if (input) input.value = selectedSucursalId;
        if (badge) {
            badge.innerText = "Destino: " + selectedSucursalNombre;
            badge.style.display = 'block';
        }
    }
}

function agregarAlCarritoTransf(productoId) {
    fetch(`/gestion/agregar-item-transf/${productoId}/`)
        .then(res => res.json())
        .then(data => { if (data.status === 'ok') recargarSoloRemito(); })
        .catch(err => console.error('Error agregar:', err));
}

function sumarItem(productoId) {
    // El botón '+' del remito llama a sumarItem
    agregarAlCarritoTransf(productoId);
}

function restarItem(productoId) {
    fetch(`/gestion/restar-item-transf/${productoId}/`)
        .then(res => res.json())
        .then(data => { if (data.status === 'ok') recargarSoloRemito(); })
        .catch(err => console.error('Error restar:', err));
}

function vaciarCarrito() {
    Swal.fire({
        title: '¿Vaciar remito?',
        text: "Se eliminarán todos los productos de la transferencia actual.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#28a745',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, vaciar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch('/gestion/vaciar-carrito-transf/')
                .then(res => res.json())
                .then(data => { if (data.status === 'ok') recargarSoloRemito(); })
                .catch(err => console.error('Error vaciar:', err));
        }
    });
}

function generarTransferencia() {
    const sucursalId = document.getElementById('input-sucursal-id')?.value;
    if (!sucursalId) {
        return Swal.fire({
            title: 'Atención',
            text: 'Por favor, seleccioná una sucursal de destino.',
            icon: 'info',
            confirmButtonColor: '#28a745'
        });
    }

    const token = typeof CSRF_TOKEN !== 'undefined' ? CSRF_TOKEN : document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (!token) return Swal.fire('Error', 'Falta token CSRF', 'error');

    const formData = new FormData();
    formData.append('sucursal_destino', sucursalId);
    formData.append('csrfmiddlewaretoken', token);

    fetch('/gestion/confirmar-transferencia/', {
        method: 'POST',
        headers: { 'X-CSRFToken': token },
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                Swal.fire({
                    title: '¡Éxito!',
                    text: data.message,
                    icon: 'success',
                    confirmButtonColor: '#28a745'
                });
                recargarPanelTransferencias();
            } else {
                Swal.fire({
                    title: 'Error',
                    text: data.message,
                    icon: 'error',
                    confirmButtonColor: '#dc3545'
                });
            }
        })
        .catch(err => {
            console.error('Error enviar transf:', err);
            Swal.fire('Error', 'No se pudo procesar la transferencia', 'error');
        });
}

function verDetalleTransferencia(id) {
    fetch(`/gestion/detalle-transferencia/${id}/`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                let html = '';
                data.items.forEach(item => {
                    html += `<tr><td>${item.producto}</td><td class="text-center small">${item.sku}</td><td class="text-center fw-bold">${item.cantidad}</td></tr>`;
                });
                document.getElementById('cuerpo-detalle-transferencia').innerHTML = html;
                document.getElementById('titulo-detalle-transferencia').innerText = `Detalle Transferencia #${id}`;
                new bootstrap.Modal(document.getElementById('modalDetalleTransferencia')).show();
            }
        });
}

function confirmarRecepcion(id) {
    Swal.fire({
        title: `¿Confirmar recepción #${id}?`,
        text: "Se actualizará el stock en tu sucursal.",
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#28a745',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, confirmar',
        cancelButtonText: 'No, esperar'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/gestion/confirmar-recepcion/${id}/`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'ok') {
                        Swal.fire({
                            title: 'Recibido',
                            text: data.message,
                            icon: 'success',
                            confirmButtonColor: '#28a745'
                        });
                        recargarPanelTransferencias();
                    } else {
                        Swal.fire('Error', data.message, 'error');
                    }
                })
                .catch(err => {
                    console.error('Error recibir:', err);
                    Swal.fire('Error', 'No se pudo confirmar la recepción', 'error');
                });
        }
    });
}

function verStockGlobal(productoId) {
    Swal.fire({
        title: 'Consultando stock...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    fetch(`/gestion-productos/ver-stock-global/${productoId}/`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                let html = `
                    <div class="table-responsive">
                        <table class="table table-sm table-striped mt-3">
                            <thead class="table-dark">
                                <tr>
                                    <th>Sucursal</th>
                                    <th class="text-center">Stock</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                data.stocks.forEach(s => {
                    const badgeClass = s.cantidad > 20 ? 'bg-success' : (s.cantidad > 5 ? 'bg-warning text-dark' : 'bg-danger');
                    html += `
                        <tr>
                            <td class="text-start fw-bold">${s.sucursal}</td>
                            <td class="text-center">
                                <span class="badge ${badgeClass} rounded-pill px-3">${s.cantidad}</span>
                            </td>
                        </tr>
                    `;
                });
                html += `</tbody></table></div>`;

                Swal.fire({
                    title: `<span class="text-primary">${data.producto}</span>`,
                    html: html,
                    confirmButtonText: 'Cerrar',
                    confirmButtonColor: '#6c757d'
                });
            } else {
                Swal.fire('Error', 'No se pudo cargar el stock global', 'error');
            }
        })
        .catch(err => {
            console.error('Error stock global:', err);
            Swal.fire('Error', 'Error de conexión al consultar stock', 'error');
        });
}
