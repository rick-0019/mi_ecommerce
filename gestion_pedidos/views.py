from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import Pedido, ItemPedido
from gestion_sucursales.models import Sucursal, Stock, MovimientoStock
import json
import pytz
from gestion_productos.models import Producto
from gestion_sucursales.services import procesar_movimiento_stock

@csrf_exempt 
def guardar_pedido(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        carrito = request.session.get('carrito', {})
        
        if not carrito:
            return JsonResponse({'status': 'error', 'message': 'Carrito vacío o ya procesado'}, status=400)

        # --- BLOQUE 1: OPERACIÓN CRÍTICA (DB Y STOCK) ---
        with transaction.atomic():
            # Intentamos buscar por nombre, si falla, buscamos por ID para ser robustos
            try:
                sucursal_obj = Sucursal.objects.get(nombre=data['sucursal'])
            except (Sucursal.DoesNotExist, ValueError):
                sucursal_obj = get_object_or_404(Sucursal, pk=data['sucursal'])
            
            # Creamos el pedido
            nuevo_pedido = Pedido.objects.create(
                cliente=data['nombre'],
                telefono=data['telefono'],
                direccion=data.get('direccion', 'RETIRO EN LOCAL'),
                sucursal=sucursal_obj,
                modalidad=data['modalidad'],
                total=float(data['total']),
                reemplazo_opcion=data.get('reemplazo_opcion', 'No permitir reemplazos'),
                nro_operacion_fiscal=data.get('nro_operacion_fiscal', ''),
                estado='PENDIENTE',
                fecha=timezone.localtime(timezone.now()) 
            )

            detalle_items_email = ""
            for key, value in carrito.items():
                # Crear Item del pedido
                ItemPedido.objects.create(
                    pedido=nuevo_pedido,
                    producto_nombre=value['nombre'],
                    sku=value.get('sku', ''),
                    cantidad=value['cantidad'],
                    precio_unitario=value['precio'],
                    subtotal=value['acumulado']
                )
                detalle_items_email += f"- {value['cantidad']}x {value['nombre']} [SKU: {value.get('sku', 'N/A')}] (${value['acumulado']})\n"

                # REGISTRO DE MOVIMIENTO CENTRALIZADO
                prod = Producto.objects.get(pk=key)
                procesar_movimiento_stock(
                    producto=prod,
                    sucursal=sucursal_obj,
                    cantidad=int(value['cantidad']), 
                    tipo='WEB', 
                    usuario=request.user if request.user.is_authenticated else None,
                    observaciones=f"Venta automática Web - Pedido #{nuevo_pedido.nro_pedido}"
                )

            # --- BLOQUE 2: LIMPIEZA DE SESIÓN ---
            request.session['carrito'] = {}
            request.session.modified = True
            request.session.save() 

        # --- BLOQUE 3: EMAIL ---
        # Enviamos email solo si el usuario está logueado y tiene correo, o podés usar data['email'] si lo agregás al form
        enviar_confirmacion_email(nuevo_pedido, detalle_items_email, request.user)

        return JsonResponse({
            'status': 'ok', 
            'nro_pedido': nuevo_pedido.nro_pedido
        })

    except Exception as e:
        raw_error = str(e).strip("[]'")
        
        # Si el error contiene la palabra 'Stock', personalizamos el mensaje
        if "Stock insuficiente" in raw_error:
            # Intentamos extraer el nombre del producto del error original
            # El error suele ser: "Stock insuficiente para NOMBRE. Actual: 0..."
            producto_nombre = raw_error.split("para ")[1].split(".")[0]
            
            mensaje_amigable = f'El producto "{producto_nombre}" no tiene stock disponible en la sucursal {sucursal_obj.nombre}.'
            titulo_alerta = "Sin Stock en Sucursal Seleccionada"
        else:
            mensaje_amigable = raw_error
            titulo_alerta = "Error al procesar"

        return JsonResponse({
            'status': 'error',
            'title': titulo_alerta,
            'message': mensaje_amigable
        }, status=400)

def enviar_confirmacion_email(pedido, detalle, usuario):
    """ Función auxiliar para no ensuciar la lógica principal """
    # Verificamos que el usuario exista y esté logueado
    if usuario and usuario.is_authenticated and hasattr(usuario, 'email') and usuario.email:
        try:
            tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
            f_local = pedido.fecha.astimezone(tz_arg)
            f_fmt = f_local.strftime("%d/%m/%Y %H:%M")

            asunto = f'Confirmación de Pedido #{pedido.nro_pedido} - Mi Ecommerce'
            cuerpo = (
                f"Hola {pedido.cliente},\n\n"
                f"¡Gracias por tu compra! Hemos recibido tu pedido #{pedido.nro_pedido} con éxito.\n\n"
                f"Fecha y Hora de la operación: {f_fmt} hs.\n\n"
                f"Detalle:\n{detalle}\n"
                f"Total: ${pedido.total}\n"
                f"Modalidad: {pedido.modalidad}\n"
                f"Criterio de Reemplazo: {pedido.reemplazo_opcion}\n"
                f"Sucursal: {pedido.sucursal.nombre}\n\n"
                f"El encargado del local ya está procesando tu solicitud."
            )
            send_mail(asunto, cuerpo, settings.EMAIL_HOST_USER, [usuario.email], fail_silently=True)
        except Exception as e:
            print(f"Error al enviar email: {e}")