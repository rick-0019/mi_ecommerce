from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # 1. Configuración visual del formulario
    fieldsets = UserAdmin.fieldsets + (
        ('Información de Rol y Sucursal', {
            'fields': ('rol', 'sucursal', 'telefono', 'direccion')
        }),
    )

    # 2. Columnas que se verán en la lista de usuarios
    list_display = ('username', 'telefono', 'email', 'rol', 'sucursal', 'is_staff')
    list_filter = ('rol', 'sucursal')

    # 3. FILTRO DE SEGURIDAD: ¿Quién puede ver a quién?
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # El Super Admin ve a absolutamente todos
        if request.user.is_superuser or request.user.rol == Usuario.SUPER_ADMIN:
            return qs
            
        # El Admin de Sucursal solo ve a los usuarios de SU sucursal
        if request.user.rol == Usuario.ADMIN_SUCURSAL:
            return qs.filter(sucursal=request.user.sucursal)
        
        # Otros roles no ven a nadie en la lista (o solo a sí mismos)
        return qs.filter(id=request.user.id)

    # 4. ASIGNACIÓN AUTOMÁTICA: Al crear un usuario, hereda la sucursal del jefe
    def save_model(self, request, obj, form, change):
        if request.user.rol == Usuario.ADMIN_SUCURSAL and not request.user.is_superuser:
            obj.sucursal = request.user.sucursal
        super().save_model(request, obj, form, change)

    # 5. RESTRICCIÓN DE EDICIÓN: El Admin de Sucursal no puede cambiarse de sucursal
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser and request.user.rol == Usuario.ADMIN_SUCURSAL:
            if 'sucursal' in form.base_fields:
                form.base_fields['sucursal'].disabled = True
        return form