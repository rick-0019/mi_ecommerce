from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
from .forms import RegistroUsuarioForm, UsuarioCRUDForm
from .models import Usuario 
from gestion_sucursales.models import Sucursal
from django.db.models import Q
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test

def registro_view(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f"¡Bienvenido {user.username}!")
            return redirect('home')
    else:
        form = RegistroUsuarioForm()
    return render(request, 'registration/registro.html', {'form': form})

@login_required
def perfil_view(request):
    user = request.user
    # 1. Traemos las sucursales para el desplegable del HTML
    sucursales = Sucursal.objects.all()
    
    if request.method == 'POST':
        nuevo_email = request.POST.get('email')
        
        # Validar email único (excepto el propio)
        if Usuario.objects.filter(email=nuevo_email).exclude(id=user.id).exists():
            messages.error(request, "Este correo electrónico ya está en uso.")
            return render(request, 'gestion_usuarios/perfil.html', {
                'usuario': user, 
                'sucursales': sucursales
            })

        # 2. Guardamos datos básicos
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = nuevo_email
        user.telefono = request.POST.get('telefono')
        user.direccion = request.POST.get('direccion')

        # 3. Guardamos la sucursal elegida
        sucursal_id = request.POST.get('sucursal')
        if sucursal_id:
            user.sucursal = Sucursal.objects.get(id=sucursal_id)
        else:
            user.sucursal = None
            
        user.save()
        messages.success(request, "Tus datos se actualizaron correctamente.")
        return redirect('home')
        
    # Agregamos 'sucursales' al contexto del GET
    return render(request, 'gestion_usuarios/perfil.html', {
        'usuario': user, 
        'sucursales': sucursales
    })

    from django.contrib.auth import authenticate, login as auth_login

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        
        # Intentamos autenticar
        user = authenticate(request, username=u, password=p)
        
        if user is not None:
            auth_login(request, user)
            messages.success(request, f"¡Hola de nuevo, {user.username}!")
            return redirect('home')
        else:
            # SI FALLA, LANZA EL ALERT ROJO
            messages.error(request, "Usuario o contraseña incorrectos. Por favor, intentá de nuevo.")
            
    return render(request, 'account/login.html') # Asegurate que la ruta sea correcta

def es_administrador(user):
    return user.is_authenticated and user.rol in ['SA', 'AS']

@login_required
@user_passes_test(es_administrador)
def lista_usuarios_ajax(request):
    usuarios = Usuario.objects.all().order_by('username')
    
    # SEGURIDAD: Si el usuario no es Super Admin, no mostramos los SA en la lista
    if request.user.rol != Usuario.SUPER_ADMIN:
        usuarios = usuarios.exclude(rol=Usuario.SUPER_ADMIN)
    
    html = render_to_string('gestion_usuarios/tabla_usuarios_fragment.html', {'usuarios': usuarios})
    return JsonResponse({'html': html})

@login_required
@user_passes_test(es_administrador)
def buscar_usuarios_ajax(request):
    query = request.GET.get('q', '').strip()
    if query:
        usuarios = Usuario.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).order_by('username')
    else:
        usuarios = Usuario.objects.all().order_by('username')
    
    # SEGURIDAD: Si el usuario no es Super Admin, no mostramos los SA en la lista
    if request.user.rol != Usuario.SUPER_ADMIN:
        usuarios = usuarios.exclude(rol=Usuario.SUPER_ADMIN)
    
    html = render_to_string('gestion_usuarios/tabla_usuarios_fragment.html', {'usuarios': usuarios})
    return JsonResponse({'html': html})

@login_required
@user_passes_test(es_administrador)
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioCRUDForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Como es creación manual desde el panel, generamos una pass temporal o pedimos setearla
            # Por simplicidad, seteamos el username como pass si no se especifica (aunque el form no tiene pass)
            # AbstractUser requiere password.
            user.set_password('Ecommerce123!') # Password por defecto
            user.save()
            return JsonResponse({'status': 'success', 'message': 'Usuario creado correctamente.'})
        return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)
    
    form = UsuarioCRUDForm()
    html = render_to_string('gestion_usuarios/modal_usuario.html', {'form': form, 'titulo': 'Crear Usuario'}, request=request)
    return JsonResponse({'html': html})

@login_required
@user_passes_test(es_administrador)
def editar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    
    # SEGURIDAD: No permitir editar Super Administradores a menos que seas uno
    if usuario.rol == Usuario.SUPER_ADMIN and request.user.rol != Usuario.SUPER_ADMIN:
        return JsonResponse({'status': 'error', 'message': 'No tienes permiso para modificar un Super Administrador.'}, status=403)
    
    if request.method == 'POST':
        form = UsuarioCRUDForm(request.POST, instance=usuario, current_user=request.user)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success', 'message': 'Usuario actualizado correctamente.'})
        return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)
    
    form = UsuarioCRUDForm(instance=usuario, current_user=request.user)
    html = render_to_string('gestion_usuarios/modal_usuario.html', {'form': form, 'usuario': usuario, 'titulo': 'Editar Usuario'}, request=request)
    return JsonResponse({'html': html})

@login_required
@user_passes_test(es_administrador)
def toggle_usuario_activo(request, usuario_id):
    if request.method == 'POST':
        usuario = get_object_or_404(Usuario, id=usuario_id)
        
        # SEGURIDAD: No permitir desactivar Super Administradores
        if usuario.rol == Usuario.SUPER_ADMIN:
            return JsonResponse({
                'status': 'error', 
                'message': 'No se puede desactivar a un Super Administrador.'
            }, status=403)
        
        usuario.is_active = not usuario.is_active
        usuario.save()
        return JsonResponse({'status': 'success', 'is_active': usuario.is_active})
    return JsonResponse({'status': 'error'}, status=400)
