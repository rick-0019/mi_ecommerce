from django import forms
from django.forms import inlineformset_factory
from .models import Producto, Categoria, Marca, ImagenProducto, HistorialPrecio
from gestion_sucursales.models import Stock

class ProductoCargaForm(forms.ModelForm):
    # Campos extra
    precio_venta = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        label="Precio de Venta ($)",
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Ej: 4650.00'})
    )
    
    precio_costo = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        label="Precio de Costo ($)", 
        required=False,
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Opcional'})
    )

    class Meta:
        model = Producto
        fields = [
            'nombre', 'categoria', 'marca', 'iva',
            'codigo_barras', 'es_sin_tacc', 'es_vegano',
            'es_oferta', 'es_novedad', 'es_proximamente', 
            'es_vegetariano', 'octogono_advertencia', 
            'tipo_envase', 'contenido_neto', 'unidad_medida',
            'peso_kg', 'volumen_m3',
            'descripcion_breve', 'descripcion_detallada', 
            'especificaciones', 'imagen_principal',
            'esta_activo', 'exclusivo_online', 'ahorrames'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

# --- FORMSET PARA HISTORIAL DE PRECIOS ---
PrecioFormSet = inlineformset_factory(
    Producto,
    HistorialPrecio,
    fields=['precio_venta', 'precio_regular', 'precio_costo', 'precio_oferta', 'es_actual'],
    extra=1,
    can_delete=True,
    widgets={
        'precio_venta': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        'precio_regular': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        'precio_costo': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        'precio_oferta': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        'es_actual': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    }
)
# --- ESTO DEBE IR FUERA DE LA CLASE ---
GaleriaFormSet = inlineformset_factory(
    Producto, 
    ImagenProducto, 
    fields=['imagen', 'orden'], 
    extra=3,  
    can_delete=True,
    widgets={
        'imagen': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
        'orden': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'style': 'width: 70px;'}),
    }
)

StockFormSet = inlineformset_factory(
    Producto,
    Stock,
    fields=['sucursal', 'cantidad', 'ubicacion_pasillo', 'stock_minimo'],
    extra=0,
    can_delete=True,
    widgets={
        'sucursal': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        'cantidad': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        'ubicacion_pasillo': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        'stock_minimo': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
    }
)
