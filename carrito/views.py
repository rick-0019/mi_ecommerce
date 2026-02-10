from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse
from .carrito import Carrito
from gestion_productos.models import Producto
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from gestion_sucursales.models import Sucursal

def agregar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    carrito.agregar(producto=producto)

    # Si la petición es AJAX (XMLHttpRequest)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Calculamos el total de items en el carrito
        # Asegúrate de que tu clase Carrito tenga una forma de darte el total
        total_items = sum(item['cantidad'] for item in request.session.get('carrito', {}).values())
        
        return JsonResponse({
            'status': 'success', 
            'unidades_totales': total_items
        })

    # Si es una petición normal (sin AJAX), redirigimos como antes
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def eliminar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    carrito.eliminar(producto=producto) # Asegúrate de tener este método en carrito.py
    return redirect("carrito_detalle")

def restar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    carrito.restar_producto(producto=producto) # Asegúrate de tener este método en carrito.py
    return redirect("carrito_detalle")

def limpiar_carrito(request):
    carrito = Carrito(request)
    carrito.limpiar_carrito() # Asegúrate de tener este método en carrito.py
    return redirect("home")

def carrito_detalle(request):
    return render(request, 'carrito_detalle.html')

def checkout(request):
    carrito = request.session.get("carrito", {})
    if not carrito:
        return redirect("home")  # No hay nada que comprar, volvemos al inicio
    
    # Aquí podrías procesar un formulario de envío más adelante
    return render(request, 'checkout.html')

@login_required(login_url='login') # Asegúrate que 'login' sea el name de tu url de login
def checkout(request):
    # Tu lógica aquí...
    return render(request, 'checkout.html')
