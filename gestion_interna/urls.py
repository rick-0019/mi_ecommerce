from django.urls import path
from . import views

app_name = 'gestion_interna'

urlpatterns = [
    path('', views.dashboard_principal, name='dashboard'),
    path('marcar-listo/<int:pedido_id>/', views.marcar_listo, name='marcar_listo'),
    path('transferencias/', views.transferencias_view, name='transferencias_view'),
    path('buscar-productos-transf/', views.buscar_productos_transferencia, name='buscar_productos_transferencia'),
    path('confirmar-transferencia/', views.confirmar_transferencia, name='confirmar_transferencia'),
    path('agregar-item-transf/<int:producto_id>/', views.agregar_item_transferencia, name='agregar_item_transferencia'),
    path('restar-item-transf/<int:producto_id>/', views.restar_item_transferencia, name='restar_item_transferencia'),
    path('vaciar-carrito-transf/', views.vaciar_carrito_transferencia, name='vaciar_carrito_transferencia'),
    path('confirmar-recepcion/<int:transferencia_id>/', views.confirmar_recepcion, name='confirmar_recepcion'),
    path('detalle-transferencia/<int:transferencia_id>/', views.obtener_detalle_transferencia, name='detalle_transferencia'),
    path('obtener-remito-ajax/', views.obtener_remito_ajax, name='obtener_remito_ajax'),
]