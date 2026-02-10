from gestion_sucursales.models import Sucursal

def importe_total_carrito(request):
    total = 0
    unidades = 0
    
    # 1. Lógica del Carrito
    if "carrito" in request.session:
        for key, value in request.session["carrito"].items():
            total += float(value["acumulado"])
            unidades += value["cantidad"]
    
    # 2. Lógica de Sucursales (Global)
    sucursales = Sucursal.objects.all()
    cantidad_sucursales = sucursales.count()
    
    return {
        "importe_total_carrito": total,
        "unidades_totales_carrito": unidades,
        # Agregamos esto para que esté disponible en todo el sitio:
        "sucursales": sucursales,
        "cantidad_sucursales": cantidad_sucursales,
        "sucursal_unica": sucursales.first() if cantidad_sucursales == 1 else None,
    }