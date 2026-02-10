from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from itertools import chain
from decimal import Decimal

# Modelos y Forms propios y de otras apps
from .models import Transferencia, ItemTransferencia
from .transferencia_session import CarritoTransferencia
from gestion_pedidos.models import Pedido
from gestion_productos.models import Producto, HistorialPrecio
from gestion_productos.forms import ProductoCargaForm, GaleriaFormSet, StockFormSet
from gestion_sucursales.models import Stock, Sucursal
from gestion_sucursales.services import procesar_movimiento_stock


def es_empleado(user):
    return user.is_authenticated and user.rol in ['SA', 'AS', 'VE']

@login_required
# Quitamos el user_passes_test para manejar el error nosotros manualmente
def dashboard_principal(request):
    user = request.user
    
    # --- FILTRO UNIFICADO (INTACTO) ---
    if user.rol not in ['SA', 'AS']:
        messages.error(request, "Acceso denegado.")
        return redirect('home')

    filtros = {'sucursal': user.sucursal} if user.rol in ['AS', 'VE'] and user.sucursal else {}

    # --- PROCESAMIENTO DEL FORMULARIO (INTACTO) ---
    if request.method == 'POST' and 'guardar_producto' in request.POST:
        form = ProductoCargaForm(request.POST, request.FILES)
        formset = GaleriaFormSet(request.POST, request.FILES)
        stock_formset = StockFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid() and stock_formset.is_valid():
            try:
                with transaction.atomic():
                    # 1. Guardar producto
                    producto = form.save()
                    
                    # 2. Crear historial de precio
                    precio_v = form.cleaned_data.get('precio_venta', 0)
                    precio_c = form.cleaned_data.get('precio_costo')
                    HistorialPrecio.objects.create(
                        producto=producto,
                        precio_venta=precio_v,
                        precio_costo=precio_c,
                        es_actual=True
                    )
                    
                    # 3. Guardar galería
                    formset.instance = producto
                    formset.save()
                    
                    # 4. Guardar stocks
                    stock_formset.instance = producto
                    stock_formset.save()
                    
                messages.success(request, f"Producto '{producto.nombre}' guardado con éxito.")
                return redirect('/gestion/?tab=productos')
            except Exception as e:
                messages.error(request, f"Error al guardar producto: {e}")
        else:
            # Si hay errores, se mostrarán en el template ya que no redirigimos
            messages.error(request, "Error en el formulario. Por favor revise los campos.")
    else:
        form = ProductoCargaForm()
        formset = GaleriaFormSet()
        
        # Ya no pre-poblamos con todas las sucursales, usamos el botón "+" dinámico
        stock_formset = StockFormSet()

    # --- LÓGICA DE PEDIDOS (INTACTO) ---
    pedidos_pendientes = Pedido.objects.filter(**filtros, estado='PENDIENTE').order_by('-fecha')
    pedidos_procesados = Pedido.objects.filter(**filtros).filter(Q(estado='PROCESADO') | Q(estado='ENTREGADO')).order_by('-fecha')[:50]
    todos = list(chain(pedidos_pendientes, pedidos_procesados))

    # --- NUEVA LÓGICA DE PRODUCTOS CON STOCK LOCAL ---
    productos_todos = Producto.objects.all().prefetch_related('precios', 'categoria').order_by('-id')
    
    # Mapear stock local para la sucursal del usuario
    if user.sucursal:
        stocks = Stock.objects.filter(sucursal=user.sucursal, producto__in=productos_todos[:100])
        stock_map = {s.producto_id: s.cantidad for s in stocks}
        for p in productos_todos:
            p.stock_local = stock_map.get(p.id, 0)
    else:
        for p in productos_todos:
            p.stock_local = None

    # --- LÓGICA DE TRANSFERENCIAS ---
    transferencias_recientes = Transferencia.objects.all().order_by('-fecha_creacion')[:10]

    return render(request, 'gestion_interna/dashboard.html', {
        'pedidos': pedidos_pendientes,
        'procesados': pedidos_procesados,
        'todos_los_pedidos': todos, 
        'sucursal': user.sucursal,
        'form': form,
        'formset': formset,
        'stock_formset': stock_formset,
        'transferencias': transferencias_recientes,
        'productos_todos': productos_todos,
        'total_productos': Producto.objects.count(),
        'total_transferencias': Transferencia.objects.count(),
    })

@login_required
@user_passes_test(es_empleado)
def marcar_listo(request, pedido_id):
    # Usamos nro_pedido porque es tu primary_key
    pedido = get_object_or_404(Pedido, nro_pedido=pedido_id)
    
    # Verificamos que el empleado pertenezca a la misma sucursal (o sea SA)
    if request.user.rol == 'SA' or pedido.sucursal == request.user.sucursal:
        pedido.estado = 'PROCESADO'
        pedido.save()
        messages.success(request, f"¡Pedido #{pedido.nro_pedido} procesado correctamente!")
    else:
        messages.error(request, "No tienes permiso para gestionar pedidos de otra sucursal.")
        
    return redirect('gestion_interna:dashboard')

def crear_transferencia(request):
    destino = request.GET.get('destino')
    # Por ahora solo renderizamos una página de carga
    # Luego procesaremos el stock aquí
    return render(request, 'gestion_interna/crear_transferencia.html', {
        'destino': destino
    })

def transferencias_view(request):
    carrito = CarritoTransferencia(request)
    user_sucursal = request.user.sucursal
    
    # Traemos las sucursales excluyendo la del usuario actual
    if request.user.is_authenticated and user_sucursal:
        sucursales = Sucursal.objects.exclude(id=user_sucursal.id)
        # 1. Transferencias ENTRANTES (Para recibir)
        transferencias_entrantes = Transferencia.objects.filter(
            destino=user_sucursal.nombre, 
            estado='EN_TRANSITO'
        ).order_by('-fecha_creacion')
        
        # 2. Transferencias SALIENTES (Historial de lo enviado)
        transferencias_enviadas = Transferencia.objects.filter(
            origen=user_sucursal.nombre
        ).order_by('-fecha_creacion')[:10]

        # 3. Transferencias RECIBIDAS (Historial de lo recibido)
        transferencias_recibidas = Transferencia.objects.filter(
            destino=user_sucursal.nombre,
            estado='COMPLETADO'
        ).order_by('-fecha_creacion')[:10]
    else:
        sucursales = Sucursal.objects.all()
        transferencias_entrantes = []
        transferencias_enviadas = []
        transferencias_recibidas = []
    
    # Calculamos el total de items del carrito actual
    total_items = sum(item.get('cantidad', 0) for item in carrito.carrito.values())
    
    return render(request, 'gestion_interna/transferencias_content.html', {
        'carrito': carrito.carrito,
        'sucursales': sucursales,
        'total_items': total_items,
        'transferencias_entrantes': transferencias_entrantes,
        'transferencias_enviadas': transferencias_enviadas,
        'transferencias_recibidas': transferencias_recibidas,
    })

def buscar_productos_transferencia(request):
    query = request.GET.get('q', '').strip()
    sucursal_origen = request.user.sucursal # Obtenemos la sucursal del usuario
    
    if len(query) < 3:
        return JsonResponse({'productos': []})

    productos = Producto.objects.filter(
        Q(nombre__icontains=query) | Q(sku__icontains=query)
    ).prefetch_related('precios').distinct()[:10]

    data = []
    for p in productos:
        # 1. Manejo de Precio (Ya corregido)
        precio = p.precio_actual()
        if isinstance(precio, (int, float, Decimal)):
            precio_formateado = f"${precio:,.2f}"
        else:
            precio_formateado = str(precio) if precio else "$0.00"

        # 2. Manejo de Stock Real por Sucursal
        # Buscamos el registro de stock específico para este producto en esta sucursal
        try:
            stock_obj = Stock.objects.get(producto=p, sucursal=sucursal_origen)
            stock_real = stock_obj.cantidad
        except Stock.DoesNotExist:
            stock_real = 0 

        data.append({
            'id': p.id,
            'nombre': p.nombre,
            'sku': p.sku or 'S/N',
            'stock': stock_real, # Ahora sí es el stock real de la sucursal
            'precio': precio_formateado
        })
    
    return JsonResponse({'productos': data})

@login_required
def dashboard_transferencias(request):
    carrito = CarritoTransferencia(request)
    # Traemos todas las sucursales para el selector de destino
    sucursales = Sucursal.objects.exclude(id=request.user.sucursal.id)
    
    return render(request, 'gestion_interna/transferencias.html', {
        'carrito': carrito.carrito,
        'sucursales': sucursales
    })

@login_required
def confirmar_transferencia(request):
    carrito_obj = CarritoTransferencia(request)
    items = carrito_obj.carrito
    destino_id = request.POST.get('sucursal_destino')

    if not items or not destino_id:
        return JsonResponse({'status': 'error', 'message': 'El carrito está vacío o no seleccionaste destino.'}, status=400)

    try:
        with transaction.atomic():
            sucursal_destino = Sucursal.objects.get(id=destino_id)
            
            # 1. Crear la cabecera
            transferencia = Transferencia.objects.create(
                origen=request.user.sucursal.nombre,
                destino=sucursal_destino.nombre,
                usuario_creador=request.user,
                estado='EN_TRANSITO'
            )

            # 2. Procesar Items y Stock
            for key, item in items.items():
                producto = get_object_or_404(Producto, id=item['producto_id'])
                
                # Crear Item
                ItemTransferencia.objects.create(
                    transferencia=transferencia,
                    producto=producto,
                    cantidad=item['cantidad']
                )

                # DESCONTAR DE ORIGEN (SALIDA)
                procesar_movimiento_stock(
                    producto=producto,
                    sucursal=request.user.sucursal,
                    cantidad=item['cantidad'],
                    tipo='SAL',
                    usuario=request.user,
                    observaciones=f"Transferencia #{transferencia.id} a {sucursal_destino.nombre}"
                )

            carrito_obj.limpiar()
            return JsonResponse({'status': 'ok', 'message': f'Transferencia #{transferencia.id} enviada correctamente.'})
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    

def error_404(request, exception):
    return render(request, '404.html', status=404)

def error_500(request):
    return render(request, '500.html', status=500)


# --- AJAX PARA CARRITO DE TRANSFERENCIAS ---

@login_required
def agregar_item_transferencia(request, producto_id):
    """Agrega un producto al carrito de transferencias en sesión"""
    carrito = CarritoTransferencia(request)
    producto = get_object_or_404(Producto, id=producto_id)
    carrito.agregar(producto)
    return JsonResponse({'status': 'ok', 'mensaje': f'{producto.nombre} agregado'})


@login_required
def restar_item_transferencia(request, producto_id):
    """Resta cantidad de un producto del carrito de transferencias"""
    carrito = CarritoTransferencia(request)
    carrito.restar(producto_id)
    return JsonResponse({'status': 'ok'})


@login_required
def vaciar_carrito_transferencia(request):
    """Vacía completamente el carrito de transferencias"""
    carrito = CarritoTransferencia(request)
    carrito.limpiar()
    return JsonResponse({'status': 'ok'})


@login_required
def confirmar_recepcion(request, transferencia_id):
    """La sucursal destino confirma que recibió los productos"""
    transferencia = get_object_or_404(Transferencia, id=transferencia_id)
    user_sucursal = request.user.sucursal

    # Seguridad: solo la sucursal destino puede confirmar
    if not user_sucursal or transferencia.destino != user_sucursal.nombre:
        return JsonResponse({'status': 'error', 'message': 'No tienes permiso para recibir esta transferencia.'}, status=403)

    if transferencia.estado != 'EN_TRANSITO':
        return JsonResponse({'status': 'error', 'message': 'Esta transferencia no está en tránsito.'}, status=400)

    try:
        with transaction.atomic():
            # Sumar stock al destino
            for item in transferencia.items.all():
                procesar_movimiento_stock(
                    producto=item.producto,
                    sucursal=user_sucursal,
                    cantidad=item.cantidad,
                    tipo='ENT',
                    usuario=request.user,
                    observaciones=f"Recepción de Transferencia #{transferencia.id}"
                )
            
            transferencia.estado = 'COMPLETADO'
            transferencia.save()
            
            return JsonResponse({'status': 'ok', 'message': f'Transferencia #{transferencia.id} recibida correctamente.'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
@login_required
def obtener_detalle_transferencia(request, transferencia_id):
    """Retorna los items de una transferencia para mostrar en un modal"""
    transferencia = get_object_or_404(Transferencia, id=transferencia_id)
    items = transferencia.items.all()
    
    data = []
    for item in items:
        data.append({
            'producto': item.producto.nombre,
            'sku': item.producto.sku,
            'cantidad': item.cantidad
        })
    
    return JsonResponse({'status': 'ok', 'items': data})
@login_required
def obtener_remito_ajax(request):
    """Retorna solo el HTML del remito (carrito) para actualizaciones AJAX"""
    carrito = CarritoTransferencia(request)
    total_items = sum(item.get('cantidad', 0) for item in carrito.carrito.values())
    return render(request, 'gestion_interna/remito_transferencia_fragment.html', {
        'carrito': carrito.carrito,
        'total_items': total_items
    })
