from django.db import models
from django.conf import settings
from gestion_sucursales.models import Sucursal

class Pedido(models.Model):
    # Opciones existentes
    MODALIDADES = [('RETIRO', 'Retiro en Sucursal'), ('ENVIO', 'Envío a Domicilio')]
    ESTADOS = [('PENDIENTE', 'Pendiente'), ('PROCESADO', 'Procesado'), ('ENTREGADO', 'Entregado')]
    
    OPCIONES_REEMPLAZO = [
        ('No permitir reemplazos', 'No permitir reemplazos'),
        ('Llamado', 'Llamado telefónico'),
        ('Criterio de la Tienda', 'Criterio de la Tienda'),
    ]

    # --- NUEVAS OPCIONES PROFESIONALES ---
    CANALES = [
        ('WEB', 'Tienda Online'),
        ('MOS', 'Venta Mostrador'),
    ]

    FORMAS_PAGO = [
    ('EFECTIVO', 'Efectivo'),
    ('DEBITO', 'Débito'),
    ('CREDITO', 'Crédito'),
    ('TRANSFERENCIA', 'Transferencia / QR'),
]

    nro_pedido = models.AutoField(primary_key=True)
    cliente = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, verbose_name="Sucursal de Despacho/Retiro")
    modalidad = models.CharField(max_length=10, choices=MODALIDADES)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='PENDIENTE')
    fecha = models.DateTimeField(auto_now_add=True)
    forma_pago = models.CharField(max_length=20, choices=FORMAS_PAGO, default='EFECTIVO')
    nro_operacion_fiscal = models.CharField(max_length=50, blank=True, null=True, help_text="Nro de ticket o cupón")
    
    reemplazo_opcion = models.CharField(
        max_length=50, 
        choices=OPCIONES_REEMPLAZO,
        default="No permitir reemplazos",
        verbose_name="Criterio de Reemplazo"
    )

    # --- NUEVOS CAMPOS INTEGRADOS ---
    canal = models.CharField(
        max_length=3, 
        choices=CANALES, 
        default='WEB',
        verbose_name="Canal de Venta"
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Vendedor que atendió"
    )

    def __str__(self):
        return f"Pedido #{self.nro_pedido} - {self.cliente} ({self.get_canal_display()})"

class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='items', on_delete=models.CASCADE)
    producto_nombre = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, blank=True, null=True)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad}x {self.producto_nombre}"


