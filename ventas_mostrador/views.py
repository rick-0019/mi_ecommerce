from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Prefetch
from django.contrib.auth.decorators import login_required, user_passes_test
from gestion_productos.models import Producto
from gestion_pedidos.models import Pedido, ItemPedido
from .ticket import TicketMostrador  # IMPORTANTE: Usamos nuestra propia lógica
from django.contrib import messages
from django.db import transaction
from gestion_sucursales.services import validar_stock, procesar_movimiento_stock
from django.core.exceptions import ValidationError
from gestion_sucursales.models import Stock

def es_vendedor(user):
    return user.is_authenticated and hasattr(user, 'rol') and user.rol in ['SA', 'AS', 'VE']

@login_required
# Quitamos el user_passes_test para que Romina pueda "entrar" y recibir el mensaje
def dashboard_ventas(request):
    user = request.user
    
    # --- FILTRO DE SEGURIDAD CON ALERT ---
    # Si es Cajera (CA) o Cliente (CL), disparamos el alert y redirigimos
    if user.rol in ['CA', 'CL']:
        messages.warning(request, f"Acceso denegado: Tu perfil de {user.get_rol_display()} no tiene permisos para realizar ventas.")
        return redirect('home')
    
    # Por seguridad extra, si no es Admin ni Vendedor, también lo sacamos
    if user.rol not in ['SA', 'AS', 'VE']:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('home')
    # -------------------------------------

    # --- TU LÓGICA ORIGINAL (SIN TOCAR NADA) ---
    ticket_obj = TicketMostrador(request)
    return render(request, 'ventas_mostrador/vender.html', {
        'ticket': ticket_obj.ticket,
        'total_ticket': ticket_obj.get_total()
    })


# Eliminamos restricciones de vendedor para que el buscador de base.html (público) funcione
def buscar_productos_ajax(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'productos': [], 'total': 0})

    # 1. Primero obtenemos el conjunto de resultados completo (Solo activos)
    queryset = Producto.objects.filter(
        Q(sku__icontains=query) |
        Q(nombre__icontains=query),
        esta_activo=True,
        categoria__activa=True
    ).select_related('categoria', 'marca').prefetch_related('precios').distinct()

    # 2. Contamos cuántos hay en total (antes de limitar a 4)
    total_encontrados = queryset.count()

    # 3. Ahora sí, tomamos solo los primeros 4 para las mini cards
    productos = queryset[:4]

    data = []
    for p in productos:
        precio_venta = p.precio_actual() 
        data.append({
            'id': p.id,
            'sku': p.sku,
            'nombre': p.nombre,
            'precio': str(precio_venta),
            'slug': p.slug,
            'marca': p.marca.nombre if p.marca else "",
            'categoria': p.categoria.nombre if p.categoria else "General",
            'imagen_url': p.imagen_principal.url if p.imagen_principal else '/static/img/no-product.png'
        })

    # Enviamos tanto la lista de 4 productos como el número total
    return JsonResponse({
        'productos': data, 
        'total': total_encontrados
    })

@login_required
def agregar_ajax(request, producto_id):
    ticket = TicketMostrador(request)
    producto = get_object_or_404(Producto, id=producto_id)
    ticket.agregar(producto)
    return JsonResponse({'status': 'ok'})

@login_required
def restar_producto_mostrador(request, producto_id):
    ticket = TicketMostrador(request)
    ticket.restar(producto_id)
    return redirect('ventas_mostrador:dashboard_ventas')

@login_required
def limpiar_carrito_ventas(request):
    ticket = TicketMostrador(request)
    ticket.limpiar()
    return redirect('ventas_mostrador:dashboard_ventas')

@login_required
def confirmar_preventa(request):
    # 1. Traemos el objeto ticket y sus datos
    ticket_obj = TicketMostrador(request)
    ticket_items = ticket_obj.ticket 
    
    if not ticket_items:
        messages.error(request, "El ticket está vacío.")
        return redirect('dashboard_ventas')

    try:
        with transaction.atomic():
            # 2. VALIDACIÓN DE STOCK MEJORADA (Acumulativa)
            errores_stock = []
            for key, item in ticket_items.items():
                prod = Producto.objects.get(id=item['producto_id'])
                if not validar_stock(prod, item['cantidad'], request.user.sucursal):
                    # Buscamos cuánto hay realmente para avisar
                    try:
                        stock_real = Stock.objects.get(producto=prod, sucursal=request.user.sucursal).cantidad
                    except Stock.DoesNotExist:
                        stock_real = 0
                    
                    errores_stock.append({
                        'producto': prod,
                        'solicitado': item['cantidad'],
                        'disponible': stock_real
                    })

            # Si encontramos errores, NO creamos el pedido. Volvemos al template mostrando los faltantes.
            if errores_stock:
                # Renderizamos la misma vista 'vender.html' pero con el contexto de errores
                return render(request, 'ventas_mostrador/vender.html', {
                    'ticket': ticket_obj.ticket,
                    'total_ticket': ticket_obj.get_total(),
                    'errores_stock': errores_stock
                })

            # 3. CREAMOS EL PEDIDO (Cabecera)
            # Usamos la lógica que te funcionó en el paso anterior
            nuevo_pedido = Pedido.objects.create(
                cliente="Consumidor Final", # Puedes cambiarlo por un nombre real
                telefono="000",
                sucursal=request.user.sucursal, 
                modalidad='RETIRO',
                total=ticket_obj.get_total(),
                estado='PENDIENTE',
                canal='MOS',
                vendedor=request.user,
                reemplazo_opcion='No permitir reemplazos'
            )

            # 3. CREAMOS LOS ITEMS (Los renglones del pedido)
            # Recorremos el diccionario del ticket para guardar cada producto
            for key, item in ticket_items.items():
                ItemPedido.objects.create(
                    pedido=nuevo_pedido,
                    producto_nombre=item['nombre'],
                    sku=item['sku'],
                    cantidad=item['cantidad'],
                    precio_unitario=item['precio'],
                    subtotal=item['acumulado']
                )

            # 4. LIMPIAMOS EL TICKET (Con paréntesis para que ejecute)
            ticket_obj.limpiar()
            messages.success(request, f"¡Pedido #{nuevo_pedido.nro_pedido} generado con éxito!")
            
    except Exception as e:
        messages.error(request, f"Error al guardar los productos: {e}")
        print(f"Error detallado: {e}")

    return redirect('ventas_mostrador:dashboard_ventas')

# --- NUEVAS FUNCIONES PARA LA CAJA  ---

def es_cajera(user):
    # Romina tiene 'CA', permitimos también a los Admin
    return user.is_authenticated and hasattr(user, 'rol') and user.rol in ['SA', 'AS', 'CA']

@login_required
@user_passes_test(es_cajera, login_url='home')
def panel_caja(request):
    """ Romina verá los pedidos pendientes de cobrar de su sucursal """
    pedidos = Pedido.objects.filter(
        Q(canal='MOS') | Q(canal='WEB', modalidad='RETIRO'),
        sucursal=request.user.sucursal
    ).exclude(estado='ENTREGADO').order_by('-fecha')

    return render(request, 'ventas_mostrador/panel_caja.html', {
        'pedidos': pedidos
    })

@login_required
@user_passes_test(es_cajera, login_url='home')
def finalizar_pedido_caja(request, nro_pedido):
    """ Romina confirma el pago y el pedido pasa a ENTREGADO """
    p = get_object_or_404(Pedido, nro_pedido=nro_pedido)
    items = ItemPedido.objects.filter(pedido=p)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. Intentamos descontar stock de todos los items
                for item in items:
                    # Buscamos el producto real (el item tiene producto_nombre y sku, 
                    # pero necesitamos el objeto Producto para el FK)
                    # Ojo: ItemPedido no tiene FK a producto en tu modelo actual?
                    # Veo en models.py 'producto_nombre'. Si no hay FK, buscamos por SKU o Nombre.
                    # Asumiremos que el SKU es confiable.
                    prod = Producto.objects.filter(sku=item.sku).first()
                    if not prod:
                        # Fallback por nombre si no hay SKU
                        prod = Producto.objects.filter(nombre=item.producto_nombre).first()
                    
                    if prod:
                        procesar_movimiento_stock(
                            producto=prod,
                            sucursal=p.sucursal,
                            cantidad=item.cantidad,
                            tipo='SAL',
                            usuario=request.user,
                            observaciones=f"Venta Mostrador #{p.nro_pedido}"
                        )
                    else:
                        # Si no encontramos el producto, es un riesgo. 
                        # Deberíamos loguearlo o frenar. Por ahora avisamos.
                        raise ValidationError(f"No se encontró producto en DB para {item.producto_nombre}")

                # 2. Si todo el stock se pudo descontar, cerramos la venta
                p.forma_pago = request.POST.get('forma_pago')
                p.nro_operacion_fiscal = request.POST.get('nro_operacion_fiscal')
                p.estado = 'ENTREGADO'
                p.save()
                messages.success(request, f"¡Venta #{p.nro_pedido} cobrada y cerrada!")
                return redirect('ventas_mostrador:panel_caja')
                
        except ValidationError as e:
            messages.error(request, f"Error de Stock al cobrar: {e}")
            # No redirigimos, nos quedamos en la misma página para que vea el error


    return render(request, 'ventas_mostrador/confirmar_pago.html', {
        'p': p,
        'items': items,
        'formas_pago': Pedido.FORMAS_PAGO
    })

def obtener_detalle_pedido(request, pedido_id):
    try:
        items = ItemPedido.objects.filter(pedido_id=pedido_id)
        data = []
        for item in items:
            data.append({
                'producto_nombre': item.producto_nombre,
                'cantidad': item.cantidad,
                'sku': item.sku,
                'subtotal': str(item.subtotal) # Convertimos a string para evitar errores de JSON
            })
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)