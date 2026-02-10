from django.contrib.auth.models import AbstractUser
from django.db import models
from gestion_sucursales.models import Sucursal

class Usuario(AbstractUser):
    SUPER_ADMIN = 'SA'
    ADMIN_SUCURSAL = 'AS'
    VENDEDOR = 'VE'
    CAJERA = 'CA'
    CLIENTE = 'CL'
    
    TIPOS_USUARIO = [
        (SUPER_ADMIN, 'Super Administrador'),
        (ADMIN_SUCURSAL, 'Administrador de Sucursal'),
        (VENDEDOR, 'Vendedor'),
        (CAJERA, 'Cajera/o'),
        (CLIENTE, 'Cliente'),
    ]

    email = models.EmailField(
        unique=True, 
        blank=False, 
        null=False,
        verbose_name="Correo electrónico",
        error_messages={
            'unique': "Ya existe un usuario con este correo electrónico.",
        }
    )
    
    sucursal = models.ForeignKey(
        Sucursal, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Sucursal asignada",
        related_name="usuarios"
    )
    
    rol = models.CharField(max_length=2, choices=TIPOS_USUARIO, default=CLIENTE)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"