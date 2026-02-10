from django.contrib import admin
from django.utils.html import format_html
from .models import Sucursal, Stock
from .models import Sucursal, Stock, MovimientoStock

# Esto permite que el stock se edite como una tabla dentro de otra ficha
class StockInline(admin.TabularInline):
    model = Stock
    extra = 1  # Te deja una fila lista para cargar una sucursal nueva
    
    # IMPORTANTE: Aquí NO ponemos 'sucursal' en readonly para que 
    # puedas elegir Madero, Luzuriaga, etc.
    fields = ('sucursal', 'cantidad', 'ubicacion_pasillo', 'stock_minimo')
    
    # Mantenemos el producto como readonly solo si estamos dentro de la sucursal,
    # pero al estar dentro de PRODUCTO, este campo se gestiona solo.

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ciudad', 'direccion')
    search_fields = ('nombre', 'ciudad')
    ordering = ('nombre',) # <--- ESTO ELIMINA LA ADVERTENCIA EN EL ADMIN
    inlines = [StockInline]

@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    # 1. Columnas visibles y filtros
    list_display = ('fecha', 'producto', 'sucursal', 'tipo', 'cantidad_coloreada', 'usuario')
    list_filter = ('fecha', 'sucursal', 'tipo', 'usuario') # Filtros laterales potentes
    search_fields = ('producto__nombre', 'observaciones')
    autocomplete_fields = ['producto']
    list_display_links = None # ESTA LÍNEA QUITA LOS LINKS PARA ENTRAR A EDITAR:
    
    # 2. Evitar que se editen movimientos ya creados
    def get_readonly_fields(self, request, obj=None):
        if obj: # Si el objeto ya existe (estás editando), todo es solo lectura
            return ('producto', 'sucursal', 'tipo', 'cantidad', 'usuario', 'fecha')
        return ('fecha',) # Si es nuevo, solo la fecha es automática

    # 3. Bloquear el botón de borrar (Opcional, pero recomendado para auditoría)
    def has_delete_permission(self, request, obj=None):
        return False 

    # 4. Asignación automática de usuario (lo que mencionamos antes)
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)

    # 5. Estética de la cantidad
    def cantidad_coloreada(self, obj):
        color = "#28a745" if obj.cantidad > 0 else "#d9534f"
        # Usamos una lógica simple: si es positivo, le pegamos el "+" a mano
        signo = "+" if obj.cantidad > 0 else ""
        return format_html(
            '<b style="color: {};">{}{} un.</b>', 
            color, 
            signo, 
            obj.cantidad
        )
    
    cantidad_coloreada.short_description = "Cantidad"

    # Para asegurar que nadie pueda cambiar nada ni por URL:
    def has_change_permission(self, request, obj=None):
        return False 