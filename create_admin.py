import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configuracion_principal.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site

User = get_user_model()

username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    print(f"Creando superusuario: {username}")
    User.objects.create_superuser(username=username, email=email, password=password)
else:
    print(f"El superusuario {username} ya existe.")

# 1. Configurar el Site (Crítico para allauth y login)
domain = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')[0]
site, created = Site.objects.get_or_create(id=1)
site.domain = domain
site.name = "Mi Ecommerce"
site.save()
print(f"Site configurado con dominio: {domain}")

# 2. Asegurar que existe la carpeta media
media_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media')
if not os.path.exists(media_path):
    os.makedirs(media_path)
    print("Carpeta media creada.")
