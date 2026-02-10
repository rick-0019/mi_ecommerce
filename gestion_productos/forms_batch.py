from django import forms
from .models import Producto, Categoria, Marca

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result

class UploadBatchForm(forms.Form):
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        label="Categoría Global",
        help_text="Se aplicará a todos los productos cargados.",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    tipo_envase = forms.ChoiceField(
        choices=Producto.TIPO_ENVASE_CHOICES,
        label="Tipo de Envase Global",
        help_text="Se aplicará a todos los productos. Puedes modificar individualmente en la grilla.",
        initial='BOT',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    imagenes = MultipleFileField(
        label="Seleccionar Imágenes",
        help_text="Formato: nombre_marca_cantidad_unidad.jpg (ej: aceite_oliva_natura_500_ml.jpg)",
        required=True,
        widget=MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'})
    )

class ProductoBatchForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'marca', 'contenido_neto', 'unidad_medida', 'tipo_envase', 'descripcion_breve', 'imagen_principal']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.Select(attrs={'class': 'form-control'}),
            'contenido_neto': forms.TextInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-control'}),
            'tipo_envase': forms.Select(attrs={'class': 'form-control'}),
            'descripcion_breve': forms.TextInput(attrs={'class': 'form-control'}),
            'imagen_principal': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La imagen es obligatoria en el modelo, pero en el form la enviamos vía temp_path
        self.fields['imagen_principal'].required = False
        # Marca es obligatoria en el modelo, nos aseguramos de que el campo sea claro
        self.fields['marca'].empty_label = "--- Seleccionar Marca ---"

    temp_image_path = forms.CharField(widget=forms.HiddenInput(), required=False)
    peso_kg = forms.DecimalField(
        max_digits=8, decimal_places=4,
        widget=forms.HiddenInput(),
        required=False,
        initial=0.0
    )
    precio_venta = forms.DecimalField(
        max_digits=12, decimal_places=2, 
        label="Precio Venta",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

ProductoBatchFormSet = forms.modelformset_factory(
    Producto,
    form=ProductoBatchForm,
    extra=0
)
