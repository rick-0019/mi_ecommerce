from django.urls import path
from . import views

app_name = 'ventas_mostrador'

urlpatterns = [
    path('', views.dashboard_ventas, name='dashboard_ventas'),
    path('buscar/', views.buscar_productos_ajax, name='buscar_productos_ajax'),
    path('agregar-ajax/<int:producto_id>/', views.agregar_ajax, name='agregar_ajax'),
    path('restar/<int:producto_id>/', views.restar_producto_mostrador, name='restar_producto_mostrador'),
    path('limpiar/', views.limpiar_carrito_ventas, name='limpiar_carrito_ventas'),
    path('confirmar/', views.confirmar_preventa, name='confirmar_preventa'),
    # RUTA PARA ROMINA (Cajera)
    path('caja/', views.panel_caja, name='panel_caja'),
    path('caja/confirmar/<int:nro_pedido>/', views.finalizar_pedido_caja, name='finalizar_pedido_caja'),
    path('detalle-pedido/<int:pedido_id>/', views.obtener_detalle_pedido, name='detalle_pedido'),
]