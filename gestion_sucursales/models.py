from django.db import models, transaction  # Importamos transaction para la seguridad
from django.conf import settings

class Sucursal(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la sucursal")
    direccion = models.CharField(max_length=255, verbose_name="Dirección")
    ciudad = models.CharField(max_length=100, verbose_name="Ciudad")

    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Stock(models.Model):
    PASILLOS_CHOICES = [
        ('ALM', 'Almacén'),
        ('BEB', 'Bebidas'),
        ('DEP', 'Deposito'),
        ('FRE', 'Frescos / Lácteos'),
        ('LIM', 'Limpieza'),
        ('PER', 'Perfumería'),
    ]

    producto = models.ForeignKey('gestion_productos.Producto', on_delete=models.CASCADE, related_name='stocks')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='stocks')
    cantidad = models.PositiveIntegerField(default=0, verbose_name="Cantidad disponible")
    stock_minimo = models.PositiveIntegerField(default=5, verbose_name="Alerta stock mínimo")
    ubicacion_pasillo = models.CharField(
        max_length=3, 
        choices=PASILLOS_CHOICES, 
        default='ALM',
        verbose_name="Sector/Pasillo"
    )

    class Meta:
        verbose_name = "Stock de Producto"
        verbose_name_plural = "Stocks de Productos"
        unique_together = ('producto', 'sucursal')

    def __str__(self):
        return f"{self.producto.nombre} en {self.sucursal.nombre}: {self.cantidad}"


class MovimientoStock(models.Model):
    TIPOS = [
        ('AJU', 'Ajuste (Rotura/Pérdida)'),
        ('ENT', 'Entrada (Compra/Proveedor)'),
        ('SAL', 'Salida (Venta/Despacho)'),
        ('WEB', 'Salida (Venta/Online)'),
        ('TRA', 'Transferencia entre sucursales'),
    ]

    producto = models.ForeignKey('gestion_productos.Producto', on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    cantidad = models.IntegerField(help_text="El sistema ajustará el signo automáticamente según el tipo.")
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-fecha']

    def save(self, *args, **kwargs):
        # Usamos transaction.atomic para asegurar que el movimiento y el stock se actualicen juntos
        with transaction.atomic():
            # Solo ejecutamos la lógica de actualización de stock si el registro es NUEVO
            if not self.pk:
                # 1. Asegurar el signo correcto de la cantidad según el tipo de movimiento
                # Salidas y Ajustes siempre restan (negativos)
                if self.tipo in ['SAL', 'AJU', 'WEB']:
                    self.cantidad = -abs(self.cantidad)
                # Entradas siempre suman (positivos)
                elif self.tipo == 'ENT':
                    self.cantidad = abs(self.cantidad)

                # 2. Buscar o crear el registro de stock para ese producto y sucursal
                stock_reg, created = Stock.objects.get_or_create(
                    producto=self.producto, 
                    sucursal=self.sucursal
                )

                # 3. Actualizar la cantidad en la tabla Stock
                stock_reg.cantidad += self.cantidad
                
                # Opcional: ELIMINADO para evitar enmascarar errores. La validación debe ser previa.
                # if stock_reg.cantidad < 0:
                #    stock_reg.cantidad = 0
                    
                stock_reg.save()
            
            # 4. Guardar el registro del movimiento (esto se ejecuta siempre para crear o editar)
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.producto.nombre} ({self.cantidad})"