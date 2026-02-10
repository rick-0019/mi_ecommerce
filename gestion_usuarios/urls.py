from django.urls import path
from . import views

app_name = 'gestion_usuarios'

urlpatterns = [
    path('lista-ajax/', views.lista_usuarios_ajax, name='lista_usuarios_ajax'),
    path('buscar-ajax/', views.buscar_usuarios_ajax, name='buscar_usuarios_ajax'),
    path('crear/', views.crear_usuario, name='crear_usuario'),
    path('editar/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'),
    path('toggle-activo/<int:usuario_id>/', views.toggle_usuario_activo, name='toggle_usuario_activo'),
]
