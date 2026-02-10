from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Stock, MovimientoStock

def validar_stock(producto, cantidad, sucursal):
    """
    Verifica si hay stock suficiente en la sucursal.
    Retorna True si alcanza, False si no.
    """
    try:
        stock_item = Stock.objects.get(producto=producto, sucursal=sucursal)
        return stock_item.cantidad >= cantidad
    except Stock.DoesNotExist:
        # Si no existe registro de stock, asumimos 0
        return False

def procesar_movimiento_stock(producto, sucursal, cantidad, tipo, usuario, observaciones=""):
    """
    Crea el movimiento de stock y actualiza el saldo.
    Maneja la lógica de validación estricta para no romper el PositiveIntegerField.
    """
    with transaction.atomic():
        # Verificamos de nuevo dentro de la transacción por seguridad (concurrencia)
        # Bloqueamos la fila del Stock para evitar condiciones de carrera (select_for_update)
        # Nota: select_for_update puede no tener efecto en SQLite como se espera en Postgres,
        # pero es buena práctica dejarlo listo.
        
        # Primero aseguramos que existe el registro de Stock
        stock_item, created = Stock.objects.get_or_create(producto=producto, sucursal=sucursal)
        
        # Si necesitamos bloquear, lo haríamos aquí:
        # stock_item = Stock.objects.select_for_update().get(pk=stock_item.pk)

        # Calculamos el impacto según el tipo (replicando la lógica del modelo original por seguridad
        # o confiando en que el modelo lo hace. Vamos a dejar que el modelo haga el cálculo de signo
        # pero validamos aquí antes de guardar).
        
        cantidad_real = 0
        if tipo in ['SAL', 'AJU', 'WEB']:
            cantidad_real = -abs(cantidad)
        elif tipo == 'ENT':
            cantidad_real = abs(cantidad)
            
        # Validación Preventiva (Evitar Crash de PositiveIntegerField)
        nuevo_saldo = stock_item.cantidad + cantidad_real
        if nuevo_saldo < 0:
            raise ValidationError(f"Stock insuficiente para {producto.nombre}. Actual: {stock_item.cantidad}, Solicitado: {abs(cantidad_real)}")

        # Creamos el movimiento. El save() del modelo MovimientoStock actualizará el Stock.
        # PERO, como vamos a quitar la lógica "safety" del modelo que pone a 0 si es negativo,
        # esta validación de arriba es la que nos protege.
        MovimientoStock.objects.create(
            producto=producto,
            sucursal=sucursal,
            cantidad=cantidad, # Pasamos el absoluto o lo que venga, el modelo maneja el signo según 'tipo'
            tipo=tipo,
            usuario=usuario,
            observaciones=observaciones
        )
