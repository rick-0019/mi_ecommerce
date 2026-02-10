from django.shortcuts import render, get_object_or_404, redirect
from django.forms import inlineformset_factory
from gestion_productos.forms import ProductoCargaForm, GaleriaFormSet
from django.db.models import Q, Min, Max
from django.db import transaction
from django.core.paginator import Paginator
from .models import Producto, Categoria, Marca, HistorialPrecio, Favorito
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ProductoCargaForm, GaleriaFormSet, StockFormSet, PrecioFormSet
from gestion_sucursales.models import Stock, Sucursal

def home(request):
    query = request.GET.get('q')
    orden = request.GET.get('orden', 'relevantes')
    
    # Usamos prefetch_related para optimizar la carga de precios
    # FILTRO: Solo productos activos de categorías activas
    lista_completa = Producto.objects.filter(esta_activo=True, categoria__activa=True).prefetch_related('precios')

    if query:
        lista_completa = lista_completa.filter(
            Q(nombre__icontains=query) | 
            Q(sku__icontains=query) |
            Q(descripcion_breve__icontains=query)
        )

    # Ordenamiento en Home (Igual que en categorías para que no falle)
    if orden in ['menor_precio', 'mayor_precio']:
        lista_completa = lista_completa.annotate(
            precio_val=Min('precios__precio_venta', filter=Q(precios__es_actual=True))
        )
        if orden == 'menor_precio':
            lista_completa = lista_completa.order_by('precio_val')
        else:
            lista_completa = lista_completa.order_by('-precio_val')
    else:
        lista_completa = lista_completa.order_by('-id')

    paginator = Paginator(lista_completa, 12) 
    page_number = request.GET.get('page')
    productos_paginados = paginator.get_page(page_number)

    return render(request, 'home.html', {
        'productos': productos_paginados,
        'query': query,
        'orden_actual': orden
    })

# --- FUNCIONES DE CATEGORÍA ---

def obtener_descendientes_ids(categoria):
    """Función recursiva para obtener todas las IDs de las subcategorías"""
    ids = [categoria.id]
    for hija in categoria.subcategorias.all(): 
        ids.extend(obtener_descendientes_ids(hija))
    return ids

def lista_productos_categoria(request, slug):
    # FILTRO: Solo permitimos ver categorías activas
    categoria_actual = get_object_or_404(Categoria, slug=slug, activa=True)
    
    # 1. Jerarquía completa (Bolsa inicial de productos activos)
    familias_ids = obtener_descendientes_ids(categoria_actual)
    productos_filtrados = Producto.objects.filter(
        categoria_id__in=familias_ids, 
        esta_activo=True
    ).select_related('marca')

    # 2. Captura de parámetros de la URL
    marcas_sel = request.GET.getlist('marca')
    subs_sel = request.GET.getlist('subcategoria')
    orden = request.GET.get('orden', 'relevantes')

    # 3. FILTRADO POR SUBCATEGORÍA (Primero para limpiar las marcas)
    if subs_sel:
        categorias_filtradas = Categoria.objects.filter(slug__in=subs_sel)
        ids_finales = []
        for cat in categorias_filtradas:
            ids_finales.extend(obtener_descendientes_ids(cat))
        productos_filtrados = productos_filtrados.filter(categoria_id__in=ids_finales)

    # 4. MARCAS DISPONIBLES (Se calculan basándose en los productos filtrados por subcategoría)
    # Esto asegura que si estás en "Aderezos", solo veas marcas de aderezos.
    marcas_disponibles = productos_filtrados.values_list('marca__nombre', flat=True).distinct().order_by('marca__nombre')

    # 5. FILTRADO POR MARCA (Se aplica después de obtener las marcas disponibles)
    if marcas_sel:
        productos_filtrados = productos_filtrados.filter(marca__nombre__in=marcas_sel)
    
    # --- LÓGICA DE PRECIOS (NUEVO) ---
    # 1. Anotamos el precio actual CORRECTO antes de filtrar
    productos_filtrados = productos_filtrados.annotate(
        precio_val=Min('precios__precio_venta', filter=Q(precios__es_actual=True))
    )

    # 2. Calculamos los límites extremos para el Slider (basado en lo filtrado hasta ahora)
    # Usamos aggregate para obtener el min y max global de esta selección
    rangos = productos_filtrados.aggregate(
        min_global=Min('precio_val'), 
        max_global=Max('precio_val') 
    )
    
    min_limit = rangos['min_global'] or 0
    max_limit = rangos['max_global'] or 1000000 # Default alto si no hay productos

    # 3. Capturamos lo que el usuario eligió en el slider
    sel_min_raw = request.GET.get('min_price')
    sel_max_raw = request.GET.get('max_price')

    # Convertimos a float/decimal con seguridad, manejando posibles comas por localización
    def parse_localized_float(val, default):
        if not val:
            return default
        try:
            # Reemplazamos coma por punto por si llega localizado
            return float(str(val).replace(',', '.'))
        except (ValueError, TypeError):
            return default

    sel_min = parse_localized_float(sel_min_raw, min_limit)
    sel_max = parse_localized_float(sel_max_raw, max_limit)

    # 4. Aplicamos el filtro de Rango de precios
    # Solo filtramos si los valors elegidos son distintos a los límites (optimización)
    # Pero para consistencia visual, filtramos siempre que sea válido dentro del rango
    if sel_min > min_limit or sel_max < max_limit:
         productos_filtrados = productos_filtrados.filter(
             precio_val__gte=sel_min, 
             precio_val__lte=sel_max
         )

    # 6. Menú lateral (Hijas directas de la categoría actual, SOLO ACTIVAS)
    subcategorias_menu = categoria_actual.subcategorias.filter(activa=True)

    # 7. ORDENAMIENTO (Mantenemos tu lógica corregida)
    # NOTA: Ya anotamos 'precio_val' arriba, así que reutilizamos eso
    if orden == 'menor_precio':
        productos_filtrados = productos_filtrados.order_by('precio_val')
    elif orden == 'mayor_precio':
        productos_filtrados = productos_filtrados.order_by('-precio_val')
    else:
        productos_filtrados = productos_filtrados.order_by('-id')

    # 8. PAGINACIÓN
    paginator = Paginator(productos_filtrados, 12) 
    page_number = request.GET.get('page')
    productos_paginados = paginator.get_page(page_number)
    
    context = {
        'categoria': categoria_actual,
        'titulo_pagina': categoria_actual.nombre,
        'productos': productos_paginados,
        'marcas_disponibles': marcas_disponibles,
        'subcategorias_disponibles': subcategorias_menu,
        'marcas_sel': marcas_sel,
        'subs_sel': subs_sel,
        'orden_actual': orden,
        # Variables Slider
        'min_limit': min_limit,
        'max_limit': max_limit,
        'sel_min': sel_min,
        'sel_max': sel_max,
    }
    return render(request, 'lista_productos.html', context)

def lista_ofertas(request):
    """Vista para mostrar todos los productos en oferta con filtros"""
    # 1. Bolsa inicial de productos (Solo ofertas activas)
    productos_filtrados = Producto.objects.filter(
        es_oferta=True, 
        esta_activo=True,
        categoria__activa=True
    ).select_related('marca', 'categoria')

    # 2. Captura de parámetros de la URL
    marcas_sel = request.GET.getlist('marca')
    subs_sel = request.GET.getlist('subcategoria')
    orden = request.GET.get('orden', 'relevantes')

    # 3. FILTRADO POR CATEGORÍA (En ofertas usamos las categorías como filtros)
    if subs_sel:
        # En el caso de ofertas, 'subcategoria' filtra por categorías que contienen estas ofertas
        # Usamos slugs de categorías de primer o segundo nivel
        categorias_filtradas = Categoria.objects.filter(slug__in=subs_sel)
        ids_finales = []
        for cat in categorias_filtradas:
            ids_finales.extend(obtener_descendientes_ids(cat))
        productos_filtrados = productos_filtrados.filter(categoria_id__in=ids_finales)

    # 4. MARCAS DISPONIBLES (Basadas en los productos en oferta)
    marcas_disponibles = productos_filtrados.values_list('marca__nombre', flat=True).distinct().order_by('marca__nombre')

    # 5. FILTRADO POR MARCA
    if marcas_sel:
        productos_filtrados = productos_filtrados.filter(marca__nombre__in=marcas_sel)
    
    # --- LÓGICA DE PRECIOS ---
    productos_filtrados = productos_filtrados.annotate(
        precio_val=Min('precios__precio_venta', filter=Q(precios__es_actual=True))
    )

    rangos = productos_filtrados.aggregate(
        min_global=Min('precio_val'), 
        max_global=Max('precio_val') 
    )
    
    min_limit = rangos['min_global'] or 0
    max_limit = rangos['max_global'] or 1000000

    sel_min_raw = request.GET.get('min_price')
    sel_max_raw = request.GET.get('max_price')

    def parse_localized_float(val, default):
        if not val: return default
        try: return float(str(val).replace(',', '.'))
        except (ValueError, TypeError): return default

    sel_min = parse_localized_float(sel_min_raw, min_limit)
    sel_max = parse_localized_float(sel_max_raw, max_limit)

    if sel_min > min_limit or sel_max < max_limit:
         productos_filtrados = productos_filtrados.filter(
             precio_val__gte=sel_min, 
             precio_val__lte=sel_max
         )

    # 6. Menú lateral (Categorías que tienen ofertas para filtrar)
    # Mostramos las categorías padre que tienen productos en oferta
    ids_cat_ofertas = Producto.objects.filter(es_oferta=True).values_list('categoria_id', flat=True).distinct()
    # Obtenemos las categorías raíz que contienen estas ofertas (o las categorías directas si preferis)
    # Por simplicidad, mostramos categorías "Padre" activas que tienen ofertas en su descendencia
    subcategorias_menu = Categoria.objects.filter(pk__in=ids_cat_ofertas, activa=True)

    # 7. ORDENAMIENTO
    if orden == 'menor_precio':
        productos_filtrados = productos_filtrados.order_by('precio_val')
    elif orden == 'mayor_precio':
        productos_filtrados = productos_filtrados.order_by('-precio_val')
    else:
        productos_filtrados = productos_filtrados.order_by('-id')

    # 8. PAGINACIÓN
    paginator = Paginator(productos_filtrados, 12) 
    page_number = request.GET.get('page')
    productos_paginados = paginator.get_page(page_number)
    
    context = {
        'titulo_pagina': 'Ofertas Imperdibles',
        'es_ofertas_page': True, # Bandera para el template
        'productos': productos_paginados,
        'marcas_disponibles': marcas_disponibles,
        'subcategorias_disponibles': subcategorias_menu,
        'marcas_sel': marcas_sel,
        'subs_sel': subs_sel,
        'orden_actual': orden,
        'min_limit': min_limit,
        'max_limit': max_limit,
        'sel_min': sel_min,
        'sel_max': sel_max,
    }
    return render(request, 'lista_productos.html', context)

def lista_ahorrames(request):
    """Vista para mostrar los productos del especial Ahorrames"""
    # 1. Bolsa inicial de productos (Solo ahorrames activos)
    productos_filtrados = Producto.objects.filter(
        ahorrames=True, 
        esta_activo=True,
        categoria__activa=True
    ).select_related('marca', 'categoria')

    # 2. Captura de parámetros de la URL
    marcas_sel = request.GET.getlist('marca')
    subs_sel = request.GET.getlist('subcategoria')
    orden = request.GET.get('orden', 'relevantes')

    # 3. FILTRADO POR CATEGORÍA
    if subs_sel:
        categorias_filtradas = Categoria.objects.filter(slug__in=subs_sel)
        ids_finales = []
        for cat in categorias_filtradas:
            ids_finales.extend(obtener_descendientes_ids(cat))
        productos_filtrados = productos_filtrados.filter(categoria_id__in=ids_finales)

    # 4. MARCAS DISPONIBLES
    marcas_disponibles = productos_filtrados.values_list('marca__nombre', flat=True).distinct().order_by('marca__nombre')

    # 5. FILTRADO POR MARCA
    if marcas_sel:
        productos_filtrados = productos_filtrados.filter(marca__nombre__in=marcas_sel)
    
    # --- LÓGICA DE PRECIOS ---
    productos_filtrados = productos_filtrados.annotate(
        precio_val=Min('precios__precio_venta', filter=Q(precios__es_actual=True))
    )

    rangos = productos_filtrados.aggregate(
        min_global=Min('precio_val'), 
        max_global=Max('precio_val') 
    )
    
    min_limit = rangos['min_global'] or 0
    max_limit = rangos['max_global'] or 1000000

    sel_min_raw = request.GET.get('min_price')
    sel_max_raw = request.GET.get('max_price')

    def parse_localized_float(val, default):
        if not val: return default
        try: return float(str(val).replace(',', '.'))
        except (ValueError, TypeError): return default

    sel_min = parse_localized_float(sel_min_raw, min_limit)
    sel_max = parse_localized_float(sel_max_raw, max_limit)

    if sel_min > min_limit or sel_max < max_limit:
         productos_filtrados = productos_filtrados.filter(
             precio_val__gte=sel_min, 
             precio_val__lte=sel_max
         )

    # 6. Menú lateral (Categorías que tienen ahorrames para filtrar)
    ids_cat_ahorrames = Producto.objects.filter(ahorrames=True).values_list('categoria_id', flat=True).distinct()
    subcategorias_menu = Categoria.objects.filter(pk__in=ids_cat_ahorrames, activa=True)

    # 7. ORDENAMIENTO
    if orden == 'menor_precio':
        productos_filtrados = productos_filtrados.order_by('precio_val')
    elif orden == 'mayor_precio':
        productos_filtrados = productos_filtrados.order_by('-precio_val')
    else:
        productos_filtrados = productos_filtrados.order_by('-id')

    # 8. PAGINACIÓN
    paginator = Paginator(productos_filtrados, 12) 
    page_number = request.GET.get('page')
    productos_paginados = paginator.get_page(page_number)
    
    context = {
        'titulo_pagina': 'Especial Ahorrames',
        'es_ofertas_page': True,
        'productos': productos_paginados,
        'marcas_disponibles': marcas_disponibles,
        'subcategorias_disponibles': subcategorias_menu,
        'marcas_sel': marcas_sel,
        'subs_sel': subs_sel,
        'orden_actual': orden,
        'min_limit': min_limit,
        'max_limit': max_limit,
        'sel_min': sel_min,
        'sel_max': sel_max,
    }
    return render(request, 'lista_productos.html', context)

def detalle_producto(request, slug):
    producto = get_object_or_404(Producto, slug=slug)
    es_favorito = False
    if request.user.is_authenticated:
        es_favorito = Favorito.objects.filter(usuario=request.user, producto=producto).exists()
    
    return render(request, 'detalle_producto.html', {
        'producto': producto,
        'es_favorito': es_favorito
    })

from django.db import transaction # Importante para la estabilidad de datos
from .forms import ProductoCargaForm, GaleriaFormSet, StockFormSet # Asegúrate de importar ambos

def crear_producto(request):
    if request.method == 'POST':
        form = ProductoCargaForm(request.POST, request.FILES)
        formset = GaleriaFormSet(request.POST, request.FILES)
        stock_formset = StockFormSet(request.POST)

        if form.is_valid() and formset.is_valid() and stock_formset.is_valid():
            try:
                with transaction.atomic():
                    # 1. Guardamos el producto
                    # Esto dispara el save() del modelo que corregimos (sin bucles)
                    producto = form.save() 
                    
                    # 2. Creamos el historial de precio INMEDIATAMENTE
                    # Usamos .get() con un valor por defecto para evitar errores de None
                    precio_v = form.cleaned_data.get('precio_venta', 0)
                    precio_c = form.cleaned_data.get('precio_costo')
                    
                    HistorialPrecio.objects.create(
                        producto=producto,
                        precio_venta=precio_v,
                        precio_costo=precio_c,
                        es_actual=True # Aseguramos que sea el vigente
                    )

                    # 3. Guardamos la galería
                    formset.instance = producto 
                    formset.save()

                    # 4. Guardamos los stocks iniciales
                    stock_formset.instance = producto
                    stock_formset.save()

                messages.success(request, f"Producto '{producto.nombre}' y galería cargados con éxito.")
                # Asegurate de que este nombre de URL sea el correcto en tu proyecto
                return redirect('/gestion/?tab=productos')

            except Exception as e:
                # Imprimí el error en la terminal para saber qué pasó exactamente
                print(f"ERROR EN CREAR_PRODUCTO: {e}")
                messages.error(request, f"Error crítico: {e}")
        else:
            # Si hay errores de validación, los mostramos para no quedar a ciegas
            print(f"ERRORES FORM: {form.errors}")
            print(f"ERRORES FORMSET: {formset.errors}")
            print(f"ERRORES STOCK FORMSET: {stock_formset.errors}")
            messages.error(request, "Datos inválidos. Revisá los campos marcados.")
    
    return redirect('/gestion/')

def crear_rapido(request, tipo):
    """
    Vista para crear Marcas o Categorías desde los modales (+) 
    del Dashboard sin recargar la página.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nombre_nuevo = data.get('nombre', '').strip()

            if not nombre_nuevo:
                return JsonResponse({'error': 'El nombre no puede estar vacío'}, status=400)

            if tipo == 'marca':
                # iexact evita duplicados si escriben "Nike" y "nike"
                obj, created = Marca.objects.get_or_create(
                    nombre__iexact=nombre_nuevo, 
                    defaults={'nombre': nombre_nuevo}
                )
            elif tipo == 'categoria':
                obj, created = Categoria.objects.get_or_create(
                    nombre__iexact=nombre_nuevo, 
                    defaults={'nombre': nombre_nuevo}
                )
            else:
                return JsonResponse({'error': 'Tipo no válido'}, status=400)

            return JsonResponse({'id': obj.id, 'nombre': obj.nombre})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
            
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def buscar_categorias_marcas_ajax(request):
    """
    Buscador para los campos de Categoría y Marca en el Dashboard.
    Retorna resultados en formato JSON para autocompletado.
    """
    tipo = request.GET.get('tipo', '') # 'categoria' o 'marca'
    q = request.GET.get('q', '').strip()

    if not q or len(q) < 2:
        return JsonResponse({'results': []})

    results = []

    if tipo == 'marca':
        # Búsqueda simple de Marcas
        marcas = Marca.objects.filter(nombre__icontains=q)[:20]
        results = [{'id': m.id, 'text': m.nombre} for m in marcas]

    elif tipo == 'categoria':
        # Búsqueda de Categorías con jerarquía
        # Ojo: __str__ es costoso si iteramos muchos, pero limitamos a 20.
        cats = Categoria.objects.filter(nombre__icontains=q)[:20]
        for c in cats:
            # Construimos la ruta completa "Abuelo > Padre > Hijo"
            full_path = str(c) 
            results.append({'id': c.id, 'text': full_path})

    return JsonResponse({'results': results})


@login_required
def toggle_favorito(request, producto_id):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        producto = get_object_or_404(Producto, id=producto_id)
        favorito, created = Favorito.objects.get_or_create(usuario=request.user, producto=producto)
        
        if not created:
            favorito.delete()
            count = Favorito.objects.filter(usuario=request.user).count()
            return JsonResponse({'status': 'removed', 'count': count})
        
        count = Favorito.objects.filter(usuario=request.user).count()
        return JsonResponse({'status': 'added', 'count': count})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def lista_favoritos(request):
    favoritos_list = Favorito.objects.filter(usuario=request.user).select_related('producto', 'producto__marca')
    
    paginator = Paginator(favoritos_list, 12)
    page_number = request.GET.get('page')
    favoritos_paginados = paginator.get_page(page_number)
    
    return render(request, 'favoritos.html', {
        'productos': favoritos_paginados, # Usamos 'productos' para que paginacion.html funcione directamente
        'cantidad_total': favoritos_list.count()
    })

@login_required
def vaciar_favoritos(request):
    if request.method == 'POST':
        Favorito.objects.filter(usuario=request.user).delete()
        messages.success(request, "Tu lista de favoritos ha sido vaciada.")
    return redirect('lista_favoritos')


# --- CRUD DE PRODUCTOS (GESTIÓN) ---

@login_required
def buscar_productos_gestion_ajax(request):
    """
    Buscador para la tabla de Gestión de Productos en el Dashboard.
    Retorna una tabla HTML (fragmento) con los resultados.
    """
    query = request.GET.get('q', '').strip()
    
    productos = Producto.objects.all().prefetch_related('precios').order_by('-id')

    if query:
        # Reemplazamos vocales en la query por un patrón que busque con/sin tilde si la DB no es inteligente
        # Pero Django con icontains suele manejarlo bien en muchas configuraciones.
        # Refuerzo: Si la DB no es PostgreSQL con unaccent, podemos usar regex o simplemente confiar en icontains
        # que suele ser suficiente para el usuario en entornos estándar.
        productos = productos.filter(
            Q(nombre__icontains=query) | 
            Q(sku__icontains=query) |
            Q(codigo_barras__icontains=query) |
            Q(categoria__nombre__icontains=query) |
            Q(marca__nombre__icontains=query)
        )

    # Limitamos a 20 para velocidad, ya que es gestión rápida
    productos = productos[:20]

    # Mapear stock local para la sucursal del usuario
    user = request.user
    if user.is_authenticated and user.sucursal:
        stocks = Stock.objects.filter(sucursal=user.sucursal, producto__in=productos)
        stock_map = {s.producto_id: s.cantidad for s in stocks}
        for p in productos:
            p.stock_local = stock_map.get(p.id, 0)
    else:
        for p in productos:
            p.stock_local = None

    return render(request, 'gestion_productos/tabla_gestion_fragment.html', {
        'productos_gestion': productos
    })


@login_required
def editar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    
    # --- LÓGICA DE STOCK SEGÚN ROL ---
    user = request.user
    if request.method == 'POST':
        form = ProductoCargaForm(request.POST, request.FILES, instance=producto)
        formset = GaleriaFormSet(request.POST, request.FILES, instance=producto)
        
        # Filtrar el formset para que el POST solo procese lo que el usuario puede ver
        if user.rol != 'SA' and user.sucursal:
            queryset_stock = Stock.objects.filter(producto=producto, sucursal=user.sucursal)
        else:
            queryset_stock = Stock.objects.filter(producto=producto)
            
        stock_formset = StockFormSet(request.POST, instance=producto, queryset=queryset_stock)
        precio_formset = PrecioFormSet(request.POST, instance=producto)

        # SI ES GERENTE, el campo sucursal puede venir vacío o deshabilitado, 
        # lo marcamos como no requerido para evitar el error de validación 'obligatorio'
        if user.rol != 'SA' and user.sucursal:
            for s_form in stock_formset:
                s_form.fields['sucursal'].required = False

        if form.is_valid() and formset.is_valid() and stock_formset.is_valid() and precio_formset.is_valid():
            try:
                with transaction.atomic():
                    producto = form.save()
                    
                    # Actualizar historial de precio...
                    precio_v = form.cleaned_data.get('precio_venta', 0)
                    precio_c = form.cleaned_data.get('precio_costo')
                    precio_actual_obj = producto.precios.filter(es_actual=True).first()
                    
                    # Si el usuario editó el precio principal arriba, creamos registro
                    if not precio_actual_obj or precio_actual_obj.precio_venta != precio_v or precio_actual_obj.precio_costo != precio_c:
                        HistorialPrecio.objects.create(
                            producto=producto, precio_venta=precio_v, precio_costo=precio_c, es_actual=True
                        )

                    formset.save()
                    precio_formset.save()
                    
                    # Al guardar el stock_formset, si es un usuario de sucursal y es nuevo (extra), 
                    # nos aseguramos de que se asigne a SU sucursal si el combo está bloqueado o faltante.
                    instances = stock_formset.save(commit=False)
                    for obj in instances:
                        if user.rol != 'SA' and user.sucursal:
                            obj.sucursal = user.sucursal
                        obj.save()
                    
                    # También manejar eliminaciones del formset
                    for obj in stock_formset.deleted_objects:
                        obj.delete()

                messages.success(request, f"Producto '{producto.nombre}' actualizado con éxito.")
                return redirect('/gestion/?tab=productos')
            except Exception as e:
                messages.error(request, f"Error al actualizar: {e}")
        else:
            messages.error(request, "Corrija los errores en el formulario.")
    else:
        # GET: Cargar datos iniciales
        precio_actual = producto.precios.filter(es_actual=True).first()
        initial_precio = {
            'precio_venta': precio_actual.precio_venta if precio_actual else 0,
            'precio_costo': precio_actual.precio_costo if precio_actual else None
        }
        
        form = ProductoCargaForm(instance=producto, initial=initial_precio)
        formset = GaleriaFormSet(instance=producto)
        precio_formset = PrecioFormSet(instance=producto)

        # Configurar StockFormSet filtrado por sucursal para no-SAs
        if user.rol != 'SA' and user.sucursal:
            queryset_stock = Stock.objects.filter(producto=producto, sucursal=user.sucursal)
            tiene_stock = queryset_stock.exists()
            
            # Si tiene stock, mostramos solo ese registro (extra=0)
            # Si no tiene, mostramos uno vacío (extra=1) pre-poblado
            extra_forms = 0 if tiene_stock else 1
            SfSet = inlineformset_factory(Producto, Stock, fields=['sucursal', 'cantidad', 'ubicacion_pasillo', 'stock_minimo'], extra=extra_forms, can_delete=True)
            
            stock_formset = SfSet(instance=producto, queryset=queryset_stock)
            
            # Pre-poblar sucursal si es nuevo y deshabilitar para que no cambien a otra
            for s_form in stock_formset:
                if not s_form.instance.id:
                    s_form.fields['sucursal'].initial = user.sucursal
                s_form.fields['sucursal'].disabled = True
        else:
            stock_formset = StockFormSet(instance=producto)

    return render(request, 'gestion_productos/editar_producto.html', {
        'form': form,
        'formset': formset,
        'stock_formset': stock_formset,
        'precio_formset': precio_formset,
        'producto': producto
    })


@login_required
def eliminar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f"Producto '{nombre}' eliminado correctamente.")
    return redirect('/gestion/?tab=productos')
@login_required
def ver_stock_sucursales(request, id):
    """
    Retorna un JSON con el stock del producto en todas las sucursales.
    """
    producto = get_object_or_404(Producto, id=id)
    sucursales = Sucursal.objects.all()
    stocks = Stock.objects.filter(producto=producto)
    
    # Mapear stock por sucursal
    mapa_stock = {s.sucursal_id: s.cantidad for s in stocks}
    
    data = []
    for s in sucursales:
        data.append({
            'sucursal': s.nombre,
            'cantidad': mapa_stock.get(s.id, 0)
        })
    
    return JsonResponse({'status': 'ok', 'producto': producto.nombre, 'stocks': data})
