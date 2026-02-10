from django.urls import path
from . import views

app_name = 'gestion_productos' # <--- OBLIGATORIO para el namespace

urlpatterns = [
    # Esta es la ruta que busca el formulario del Dashboard
    path('crear/', views.crear_producto, name='crear'),
    path('crear-rapido/<str:tipo>/', views.crear_rapido, name='crear_rapido'), 
    path('buscar-ajax/', views.buscar_categorias_marcas_ajax, name='buscar_ajax'),
    path('buscar-gestion-ajax/', views.buscar_productos_gestion_ajax, name='buscar_gestion_ajax'),
    path('editar/<int:id>/', views.editar_producto, name='editar'),
    path('eliminar/<int:id>/', views.eliminar_producto, name='eliminar'),
    path('ver-stock-global/<int:id>/', views.ver_stock_sucursales, name='ver_stock_global'),
]
