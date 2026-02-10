import os
import uuid
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from .models import Producto, Categoria, Marca, HistorialPrecio
from .forms_batch import UploadBatchForm, ProductoBatchForm
from django.forms import formset_factory

@method_decorator(staff_member_required, name='dispatch')
class CargaMasivaView(View):
    template_step1 = 'admin/gestion_productos/carga_masiva_paso1.html'
    template_step2 = 'admin/gestion_productos/carga_masiva_paso2.html'

    def get(self, request):
        form = UploadBatchForm()
        return render(request, self.template_step1, {
            'form': form,
            'title': 'Carga Masiva - Paso 1: Subida'
        })

    def post(self, request):
        if 'confirm_save' in request.POST:
            return self.process_save(request)
        
        form = UploadBatchForm(request.POST, request.FILES)
        if form.is_valid():
            categoria_id = form.cleaned_data['categoria'].id
            tipo_envase_global = form.cleaned_data['tipo_envase']
            files = form.cleaned_data['imagenes']
            
            # Asegurar que el directorio temporal existe en el sistema de archivos local
            # si estamos usando FileSystemStorage (que es lo común por defecto)
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_batch')
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)

            initial_data = []
            for f in files:
                # 1. Guardar temporalmente
                temp_name = f"temp_batch/{uuid.uuid4()}_{f.name}"
                path = default_storage.save(temp_name, ContentFile(f.read()))
                
                # 2. Parsear nombre
                parsed_data = self.parse_filename(f.name)
                parsed_data['temp_image_path'] = path
                parsed_data['categoria'] = categoria_id
                parsed_data['tipo_envase'] = tipo_envase_global
                initial_data.append(parsed_data)
            
            ProductoFormSet = formset_factory(ProductoBatchForm, extra=0)
            formset = ProductoFormSet(initial=initial_data)
            
            return render(request, self.template_step2, {
                'formset': formset,
                'categoria_id': categoria_id,
                'title': 'Carga Masiva - Paso 2: Validación'
            })
        
        return render(request, self.template_step1, {'form': form})

    def parse_filename(self, filename):
        # 1. Limpieza básica: quitar extensión y reemplazar guiones por espacios
        name_only = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
        # Quitar puntos al final si existen (ej: ml.)
        name_only = name_only.strip().strip('.')
        
        parts = name_only.split()
        
        data = {
            'nombre': name_only, # Fallback
            'marca': None,
            'contenido_neto': '',
            'unidad_medida': 'UN',
            'descripcion_breve': name_only.title(),
            'precio_venta': 0.0,
            'peso_kg': 0.0  # Nuevo campo autocalculado
        }

        # 2. Buscar Contenido Neto (Número) y Unidad
        # Buscamos de atrás para adelante el primer número
        idx_num = -1
        for i in range(len(parts) - 1, -1, -1):
            p = parts[i]
            # Intentar ver si es un número (ej: 500, 1.5, 1,5)
            clean_p = p.replace(',', '.')
            try:
                float(clean_p)
                idx_num = i
                data['contenido_neto'] = clean_p
                break
            except ValueError:
                continue
        
        if idx_num != -1:
            # La unidad es lo que sigue al número (si hay algo)
            if idx_num + 1 < len(parts):
                unidad_raw = parts[idx_num + 1].upper().strip('.')
                unidades_map = {
                    'ML': 'ML',
                    'MILILITROS': 'ML',
                    'CC': 'ML',      # Centímetros cúbicos = mililitros
                    'CM3': 'ML',     # Ídem
                    'GR': 'GR',
                    'GRAMOS': 'GR',
                    'G': 'GR',       # Gramos abreviado
                    'KG': 'KG',
                    'KILO': 'KG',
                    'KILOGRAMOS': 'KG',
                    'K': 'KG',       # Kilo abreviado
                    'L': 'LT',
                    'LT': 'LT',
                    'LITROS': 'LT',
                    'LTS': 'LT',     # Litros plural
                    'UN': 'UN',
                    'UNIDAD': 'UN',
                }
                data['unidad_medida'] = unidades_map.get(unidad_raw, 'UN')
            
            # Nombre + Marca es todo lo anterior al número
            name_vibe = " ".join(parts[:idx_num]).title()
            data['nombre'] = name_vibe
        
        # 3. Búsqueda de Marca (en todo el nombre)
        # Esto es más lento pero más seguro
        marcas = Marca.objects.all()
        found_marca = None
        for m in marcas:
            if m.nombre.lower() in name_only.lower():
                found_marca = m
                break
        
        if found_marca:
            data['marca'] = found_marca.id
        
        full_name = f"{data['nombre']} {data['contenido_neto']}{data['unidad_medida']}".strip()
        data['nombre'] = full_name
        data['descripcion_breve'] = full_name
        
        # 4. Calcular peso_kg automáticamente
        # Si es GR o ML, dividimos entre 1000 para obtener KG o LT
        # Si es KG o LT, lo usamos directamente
        try:
            contenido = float(data['contenido_neto'])
            unidad = data['unidad_medida']
            if unidad in ['GR', 'ML']:
                data['peso_kg'] = round(contenido / 1000, 4)
            elif unidad in ['KG', 'LT']:
                data['peso_kg'] = round(contenido, 4)
            else:
                data['peso_kg'] = 0.0
        except (ValueError, TypeError):
            data['peso_kg'] = 0.0
        
        return data

    def process_save(self, request):
        ProductoFormSet = formset_factory(ProductoBatchForm, extra=0)
        formset = ProductoFormSet(request.POST)
        categoria_id = request.POST.get('categoria_id')
        
        try:
            categoria = Categoria.objects.get(id=categoria_id)
        except Categoria.DoesNotExist:
            messages.error(request, "La categoría seleccionada no es válida.")
            return redirect('admin_gestion_productos_producto_batch_upload')

        if formset.is_valid():
            created_count = 0
            temp_files_to_delete = []  # Colectamos paths para borrar DESPUÉS del atomic
            
            try:
                with transaction.atomic():
                    for form in formset:
                        data = form.cleaned_data
                        temp_path = data.get('temp_image_path')
                        
                        # Instanciar el producto (todavía no guardamos)
                        producto = Producto(
                            nombre=data['nombre'],
                            marca=data['marca'],
                            categoria=categoria,
                            contenido_neto=data['contenido_neto'],
                            unidad_medida=data['unidad_medida'],
                            tipo_envase=data.get('tipo_envase', 'UNI'),
                            descripcion_breve=data['descripcion_breve'],
                            peso_kg=data.get('peso_kg', 0.0),
                            esta_activo=True
                        )
                        
                        # Mover imagen si existe antes del save final
                        if temp_path and default_storage.exists(temp_path):
                            filename = os.path.basename(temp_path)
                            # Quitamos el prefijo uuid (formato: uuid_nombre.jpg)
                            parts = filename.split('_')
                            original_filename = "_".join(parts[1:]) if len(parts) > 1 else filename
                            final_name = f"{original_filename}" # Django añade productos/fotos/ por el upload_to
                            
                            with default_storage.open(temp_path) as f:
                                producto.imagen_principal.save(final_name, ContentFile(f.read()), save=False)
                            
                            # Marcar para borrar DESPUÉS del commit exitoso
                            temp_files_to_delete.append(temp_path)
                        
                        # Ahora sí guardamos el producto (crea Slug/SKU)
                        producto.save()
                        
                        # Crear historial de precio
                        HistorialPrecio.objects.create(
                            producto=producto,
                            precio_venta=data['precio_venta'],
                            es_actual=True
                        )
                        created_count += 1
                
                # ÉXITO: Ahora sí borramos los archivos temporales
                # (fuera del atomic, después del commit)
                for temp_path in temp_files_to_delete:
                    try:
                        if default_storage.exists(temp_path):
                            default_storage.delete(temp_path)
                    except Exception:
                        pass  # Ignoramos errores de limpieza
                
                messages.success(request, f"Se cargaron con éxito {created_count} productos.")
                return redirect('admin:gestion_productos_producto_changelist')
            except Exception as e:
                messages.error(request, f"Error al procesar la carga: {str(e)}")
        else:
            messages.error(request, "Hay errores en la grilla de productos.")
            return render(request, self.template_step2, {
                'formset': formset,
                'categoria_id': categoria_id,
                'title': 'Carga Masiva - Paso 2: Validación (Con Errores)'
            })
        
        return redirect('admin:gestion_productos_producto_changelist')
