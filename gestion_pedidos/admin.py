from django.contrib import admin
from .models import Pedido, ItemPedido

# Esto permite ver los productos comprados dentro del detalle del Pedido
class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0 
    
    # Agregamos 'sku' aquí, que es donde realmente existe en la base de datos
    fields = ('sku', 'producto_nombre', 'cantidad', 'precio_unitario', 'subtotal')
    
    # Es importante que también esté en readonly para que no tire error si no es editable
    readonly_fields = ('sku', 'producto_nombre', 'cantidad', 'precio_unitario', 'subtotal')
    can_delete = False 

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    # AQUÍ NO DEBE IR EL SKU. El pedido (cabecera) no tiene un SKU único.
    list_display = ('nro_pedido', 'fecha_formateada', 'cliente', 'canal',      # <--- Nueva columna
        'vendedor', 'sucursal', 'modalidad', 'nro_operacion_fiscal', 'total', 'estado')
    
    # AQUÍ TAMPOCO. No se puede filtrar la lista de pedidos por un campo de sus items.
    list_filter = ('estado', 'sucursal', 'modalidad', 'fecha')
    
    search_fields = ('nro_pedido', 'cliente', 'telefono')
    ordering = ('-fecha',)
    inlines = [ItemPedidoInline]

    def fecha_formateada(self, obj):
        return obj.fecha.strftime("%d/%m/%Y %H:%M")
    fecha_formateada.short_description = 'Fecha y Hora'


