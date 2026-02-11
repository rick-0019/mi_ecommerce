from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from gestion_productos.views import home
from gestion_productos import views
from gestion_usuarios.views import login_view, registro_view, perfil_view
from gestion_pedidos.views import guardar_pedido
from django.conf.urls import handler404

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    
    # --- USUARIOS (ORDEN CRÍTICO) ---
    path('accounts/login/', login_view, name='login'), # Tu vista personalizada primero
    path('registro/', registro_view, name='registro'),
    path('perfil/', perfil_view, name='perfil'),
    
    # Librerías externas después
    path('accounts/', include('allauth.urls')), 
    path('accounts/', include('django.contrib.auth.urls')), 

    # --- PRODUCTOS ---
    path('producto/<slug:slug>/', views.detalle_producto, name='detalle_producto'),
    path('categoria/<slug:slug>/', views.lista_productos_categoria, name='categoria'),
    path('ofertas/', views.lista_ofertas, name='ofertas'),
    path('ahorrames/', views.lista_ahorrames, name='ahorrames'),
    path('favoritos/toggle/<int:producto_id>/', views.toggle_favorito, name='toggle_favorito'),
    path('favoritos/', views.lista_favoritos, name='lista_favoritos'),
    path('favoritos/vaciar/', views.vaciar_favoritos, name='vaciar_favoritos'),
    
    # --- GESTIÓN ---
    path('gestion-productos/', include('gestion_productos.urls', namespace='gestion_productos')),
    path('carrito/', include('carrito.urls')),
    path('guardar-pedido/', guardar_pedido, name='guardar_pedido'),
    path('gestion/', include('gestion_interna.urls')),
    path('gestion-usuarios/', include('gestion_usuarios.urls', namespace='gestion_usuarios')),
    path('dashboard/', lambda r: redirect('/gestion/')), # Redirección de cortesía
    path('ventas/', include('ventas_mostrador.urls')),
    
]

handler404 = 'gestion_interna.views.error_404'
handler500 = 'gestion_interna.views.error_500'

from django.urls import re_path
from django.views.static import serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
