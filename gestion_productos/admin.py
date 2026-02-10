import json
from django.contrib import admin
from django.db import models
from django import forms
from django.urls import path
from django.utils.html import format_html
from django.db.models import Sum
from .models import Producto, Categoria, Marca, HistorialPrecio, ImagenProducto
from .views_batch import CargaMasivaView
from gestion_sucursales.admin import StockInline

# =================================================================
# 1. WIDGET PERSONALIZADO (Debe estar AFUERA de las otras clases)
# =================================================================
class PrettyJSONWidget(forms.Textarea):
    def format_value(self, value):
        try:
            if value is None or value == "":
                return ""
            if isinstance(value, str):
                value = json.loads(value)
            # Indent=4 crea los espacios, ensure_ascii=False permite tildes y Ñ
            return json.dumps(value, indent=4, ensure_ascii=False)
        except Exception:
            return value

# =================================================================
# 2. DEFINICIÓN DE INLINES
# =================================================================
class ImagenProductoInline(admin.TabularInline):
    model = ImagenProducto
    extra = 3 

class PrecioInline(admin.TabularInline):
    model = HistorialPrecio
    extra = 1
    max_num = 10
    fields = ['precio_venta', 'precio_regular', 'precio_costo', 'precio_oferta', 'es_actual', 'fecha_inicio']
    readonly_fields = ['fecha_inicio']

# =================================================================
# 3. REGISTRO DE CATEGORÍAS Y MARCAS
# =================================================================
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'padre', 'activa', 'orden')
    list_editable = ('activa', 'orden')
    list_filter = ('activa', 'padre') 
    search_fields = ('nombre',)
    prepopulated_fields = {'slug': ('nombre',)}
    autocomplete_fields = ['padre']
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('nombre')

@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('nombre')

# =================================================================
# 4. REGISTRO DE PRODUCTO PROFESIONAL
# =================================================================
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    
    list_display = (
        'nombre', 'marca', 'categoria', 'precio_actual',
        'precio_por_unidad_medida', 'es_oferta',
        'stock_total', 'esta_activo'
    )

    # AQUÍ APLICAMOS EL WIDGET Y EL CSS PARA FORZAR EL FORMATO
    formfield_overrides = {
        models.TextField: {
            'widget': forms.Textarea(attrs={'rows': 15, 'style': 'width: 95%;'})
        },
        models.JSONField: {
            'widget': PrettyJSONWidget(attrs={
                'rows': 20, 
                'style': 'width: 95%; color: #00ff00; background: #1a1a1a; font-family: monospace; white-space: pre-wrap;'
            })
        },
    }
    
    list_filter = ('categoria', 'marca', 'es_sin_tacc', 'es_oferta', 'es_novedad')
    search_fields = ('nombre', 'sku', 'codigo_barras')
    prepopulated_fields = {'slug': ('nombre',)}
    readonly_fields = ('sku',)
    autocomplete_fields = ['categoria', 'marca']
    inlines = [StockInline, PrecioInline, ImagenProductoInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('carga-masiva/', self.admin_site.admin_view(CargaMasivaView.as_view()), name='gestion_productos_producto_batch_upload'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_batch_button'] = True
        return super().changelist_view(request, extra_context=extra_context)

    fieldsets = (
        ('Identificación y Clasificación', {
            'fields': ('nombre', 'slug', 'sku', 'codigo_barras', 'marca', 'categoria', 'iva')
        }),
        ('Marketing y Etiquetas', {
            'fields': (
                'es_oferta',
                ('ahorrames', 'exclusivo_online'),
                ('etiqueta_descuento', 'es_novedad', 'es_proximamente', 'es_sin_tacc', 'es_vegano', 'es_vegetariano'),
            'octogono_advertencia'
            ),
            'description': 'Configura los carteles de oferta y filtros de salud.'
        }),
        ('Empaque y Visualización', {
            'fields': (
                'tipo_envase', ('contenido_neto', 'unidad_medida'),
                'precio_por_unidad_medida', 'imagen_principal', 'esta_activo'
            )
        }),
        ('Especificaciones de Producto (Rubros Especiales)', {
            'fields': ('especificaciones',),
            'description': 'Se verá ordenado automáticamente con sangría.'
        }),
        ('Descripción y Logística', {
            'fields': ('descripcion_breve', 'descripcion_detallada', 'peso_kg', 'volumen_m3')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('nombre')

    def stock_total(self, obj):
        total = obj.stocks.aggregate(total=Sum('cantidad'))['total'] or 0
        color = '#d9534f' if total <= 5 else '#28a745'
        icon = '⚠️' if total <= 5 else '✅'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {} un.</span>',
            color, icon, total
        )
    
    stock_total.short_description = 'Stock Disponible'
    stock_total.admin_order_field = 'stocks__cantidad'
    
    