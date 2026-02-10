from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario

class RegistroUsuarioForm(UserCreationForm):
    # Agregamos los campos extra de tu modelo
    first_name = forms.CharField(label="Nombre", max_length=30, required=True)
    last_name = forms.CharField(label="Apellido", max_length=30, required=True)
    email = forms.EmailField(label="Correo electrónico", required=True)
    telefono = forms.CharField(label="Teléfono", max_length=20, required=False)
    direccion = forms.CharField(label="Dirección", widget=forms.Textarea(attrs={'rows': 2}), required=False)

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'telefono', 'direccion')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicamos clases de Bootstrap a todos los campos
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class UsuarioCRUDForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'rol', 'sucursal', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'sucursal': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        
        # SEGURIDAD: Si estamos editando un Super Admin, el rol no puede cambiarse
        if self.instance and self.instance.pk and self.instance.rol == Usuario.SUPER_ADMIN:
            self.fields['rol'].widget.attrs['disabled'] = 'disabled'
            self.fields['rol'].help_text = "El rol de Super Administrador no puede ser modificado."
            self.fields['is_active'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_active'].help_text = "Un Super Administrador no puede ser desactivado."
        
        # SEGURIDAD: Si el usuario actual NO es Super Admin, no puede asignar el rol SA
        if self.current_user and self.current_user.rol != Usuario.SUPER_ADMIN:
            # Filtramos las opciones de rol para excluir Super Admin
            choices = [(k, v) for k, v in Usuario.TIPOS_USUARIO if k != Usuario.SUPER_ADMIN]
            self.fields['rol'].choices = choices

    def clean_rol(self):
        # Prevenir cambios de rol en Super Admin por POST directo
        if self.instance and self.instance.pk and self.instance.rol == Usuario.SUPER_ADMIN:
            return Usuario.SUPER_ADMIN  # Forzamos que permanezca como SA
        return self.cleaned_data.get('rol')

    def clean_is_active(self):
        # Prevenir desactivación de Super Admin por POST directo
        if self.instance and self.instance.pk and self.instance.rol == Usuario.SUPER_ADMIN:
            return True  # Forzamos que permanezca activo
        return self.cleaned_data.get('is_active')