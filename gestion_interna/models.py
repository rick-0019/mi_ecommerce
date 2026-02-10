from django.db import models
from django.conf import settings 

class Transferencia(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_TRANSITO', 'En Tránsito'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    origen = models.CharField(max_length=100, default="Madero")
    destino = models.CharField(max_length=100)
    usuario_creador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')

    def __str__(self):
        return f"Transferencia #{self.id} - {self.origen} a {self.destino}"

class ItemTransferencia(models.Model):
    transferencia = models.ForeignKey(Transferencia, related_name='items', on_delete=models.CASCADE)
    # Referencia cruzada segura a la app de productos
    producto = models.ForeignKey('gestion_productos.Producto', on_delete=models.CASCADE) 
    cantidad = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"
