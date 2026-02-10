from django.db import models
from django.utils.text import slugify

# 1. CATEGORÍA (Debe ir primero para que Producto pueda verla)
class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    
    padre = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subcategorias',
        verbose_name="Categoría Superior (Padre)"
    )
    
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.ImageField(upload_to='categorias/', null=True, blank=True)
    orden = models.PositiveIntegerField(default=0, help_text="Para ordenar en el menú")
    activa = models.BooleanField(default=True, verbose_name="¿Activa?", help_text="Desmarcar para ocultar esta categoría y sus productos de la tienda.")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        full_path = [self.nombre]
        k = self.padre
        while k is not None:
            full_path.append(k.nombre)
            k = k.padre
        return ' > '.join(reversed(full_path))

    def get_ancestros(self):
        """Retorna una lista de objetos Categoria desde la raíz hasta la actual"""
        ancestros = []
        p = self.padre
        while p is not None:
            ancestros.insert(0, p)
            p = p.padre
        return ancestros

# 2. MARCA
class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    imagen = models.ImageField(upload_to='marcas/', null=True, blank=True)

    def __str__(self):
        return self.nombre

# 3. PRODUCTO
class Producto(models.Model):
    TIPO_ENVASE_CHOICES = [
        ('AER', 'Bandeja'),
        ('BAN', 'Bandeja'),
        ('BOL', 'Bolsa'),
        ('BOT', 'Botella'),
        ('BRIK', 'Tetrabrik'),
        ('CAJ', 'Caja'),
        ('FRAS', 'Frasco'),
        ('LATA', 'Lata'),
        ('MAP', 'Maple'),
        ('UNI', 'Unidad/Suelto'),
        ('PAQ', 'Paquete'),
        ('SAC', 'Sachet'),
    ]

    # Lista de opciones para la carga profesional
    UNIDADES_MEDIDA_CHOICES = [
        ('GR', 'Gramos'),
        ('KG', 'Kilogramos'),
        ('CM3', 'cm³'),
        ('ML', 'Ml'),
        ('LT', 'Litros'),
        ('UN', 'Unidades'),
    ]

    #IVA

    IVA_CHOICES = [
        (21.00, '21% (General)'),
        (10.50, '10.5% (Reducido)'),
        (0.00, '0% (Exento)'),
    ]

    def get_precio_actual_obj(self):
        """Retorna el objeto HistorialPrecio actual"""
        return self.precios.filter(es_actual=True).first()

    def precio_actual(self):
        """Retorna el valor numérico del precio de venta actual"""
        precio = self.get_precio_actual_obj()
        return precio.precio_venta if precio else 0

    def precio_antes(self):
        """Retorna el precio regular si es mayor al de venta (para tachar)"""
        precio = self.get_precio_actual_obj()
        if precio and precio.precio_regular > precio.precio_venta:
            return precio.precio_regular
        return None

    def descuento_porcentaje(self):
        """Calcula el porcentaje de descuento basado en precio_regular y precio_venta"""
        precio = self.get_precio_actual_obj()
        if precio and precio.precio_regular > 0 and precio.precio_venta < precio.precio_regular:
            descuento = ((precio.precio_regular - precio.precio_venta) / precio.precio_regular) * 100
            return int(round(descuento))
        return 0

    # Identificación Básica
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    sku = models.CharField(max_length=50, unique=True, blank=True, verbose_name="Código SKU")
    codigo_barras = models.CharField(max_length=100, blank=True, null=True)
    
    # Clasificación
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos")
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT, related_name="productos")
    iva = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        choices=IVA_CHOICES, 
        default=21.00,
        verbose_name="Porcentaje de IVA"
    )
    
    # Marketing y Etiquetas (Nivel Coto)
    es_oferta = models.BooleanField(default=False, verbose_name="¿Es Oferta?")
    es_novedad = models.BooleanField(default=False, verbose_name="¿Es Novedad?")
    es_proximamente = models.BooleanField(default=False, verbose_name="¿Es Próximamente?")
    exclusivo_online = models.BooleanField(default=False, verbose_name="Exclusivo Online")
    ahorrames = models.BooleanField(default=False, verbose_name="Ahorrames?")
    
    # Etiquetas de Salud y Dieta
    es_sin_tacc = models.BooleanField(default=False, verbose_name="¿Es Sin TACC?")
    es_vegano = models.BooleanField(default=False, verbose_name="¿Es Vegano?")
    es_vegetariano = models.BooleanField(default=False, verbose_name="¿Es Vegetariano?")
    octogono_advertencia = models.CharField(max_length=100, blank=True, null=True, help_text="Ej: Exceso en Azúcares, Exceso en Sodio")
    
    etiqueta_descuento = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Ej: 25% DTO o 2x1"
    )
    
    # Envase y Medidas
    tipo_envase = models.CharField(max_length=4, choices=TIPO_ENVASE_CHOICES, default='UNI', verbose_name="Tipo de Envase")
    contenido_neto = models.CharField(max_length=50, help_text="Ej: 500, 1.5", blank=True, null=True)
    
    # Nuevo campo solicitado con el menú desplegable
    unidad_medida = models.CharField(
        max_length=3, 
        choices=UNIDADES_MEDIDA_CHOICES, 
        default='UN',
        verbose_name="Unidad de Medida"
    )

    precio_por_unidad_medida = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Precio por Kilo/Litro"
    )
    def plantilla_descripcion_html():
            return """<p><b>Nombre del Producto</b></p>
        <p>Transformá tu living en un cine con imágenes ultra nítidas...</p>

        <p><b>Por qué elegir este producto:</b></p>
        <ul>
            <li>Característica destacada 1.</li>
            <li>Característica destacada 2.</li>
            <li>Diseño delgado y moderno.</li>
        </ul>
        <p>Viví cada escena como nunca...</p>"""
    # Descripción y Multimedia
    descripcion_breve = models.CharField(max_length=255)
    descripcion_detallada = models.TextField(
        blank=True, 
        null=True, 
        default=plantilla_descripcion_html, # <--- Se asigna la función aquí
        verbose_name="Descripción detallada"
    )
    imagen_principal = models.ImageField(upload_to='productos/fotos/')

    # 1. Definimos la función de la guía (Ponela arriba de la clase Producto)
    def guia_especificaciones():
            return {
                        "Dimensiones": {
                            "Dimensiones con Base": "758x1234x237 mm",
                            "Dimensiones sin Base": "710x1234x60 mm",
                            "Peso con Base": "17 Kg",
                            "Peso sin Base": "16,4 Kg",
                            "Pulgadas": "55\""
                        },
                        "Características Técnicas": {
                            "Definición": "4K Ultra HD",
                            "Resolución": "3,840 x 2,160",
                            "Tecnología TV": "LED",
                            "Smart TV": "Sí",
                            "Sintonizador Digital": "Sí",
                            "Voltaje": "220V"
                        },
                        "Conectividad": {
                            "Wifi + Bluetooth": "Sí",
                            "Entradas HDMI": "3",
                            "Entradas USB": "1",
                            "Audio Formatos": "Estéreo"
                        },
                        "Información General": {
                            "Modelo": "UN55DU7000GCZB",
                            "Origen": "Nacional (Argentina)",
                            "Color": "Negro",
                            "Incluye": "Control remoto, manual, cable power",
                            "Garantía/Soporte": "samsung.com"
                        }
                    }

    # --- NUEVO CAMPO PARA RUBROS FLEXIBLES (ELECTRO, HOGAR, ETC) ---
    especificaciones = models.JSONField(
        blank=True, 
        null=True, 
        default=guia_especificaciones, # <--- CAMBIAMOS dict POR NUESTRA FUNCIÓN
        verbose_name="Especificaciones Técnicas",
        help_text="Complete los valores entre comillas."
    )
    
    # Logística
    peso_kg = models.DecimalField(max_digits=8, decimal_places=4, default=0.0)
    volumen_m3 = models.DecimalField(max_digits=8, decimal_places=4, default=0.0)
    
    esta_activo = models.BooleanField(default=True)
    creado_el = models.DateTimeField(auto_now_add=True)
    actualizado_el = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    @property
    def precio_sin_impuestos(self):
        """
        Calcula el valor neto partiendo del precio con IVA incluido.
        Fórmula: Precio Total / (1 + (IVA / 100))
        """
        precio_obj = self.precios.filter(es_actual=True).first()
        if precio_obj and precio_obj.precio_venta:
            divisor = 1 + (float(self.iva) / 100)
            return round(float(precio_obj.precio_venta) / divisor, 2)
        return 0

    def save(self, *args, **kwargs):
        # 1. Slug y SKU
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.nombre)
        
        if not self.sku:
            ultimo_p = Producto.objects.order_by('id').last()
            nuevo_id = (ultimo_p.id + 1) if ultimo_p else 1
            self.sku = f"{nuevo_id:08d}"

        # 2. Guardado inicial (para que el producto exista en la DB)
        super().save(*args, **kwargs)

        # 3. Intento de cálculo inmediato
        precio_actual = self.precios.filter(es_actual=True).first()
        
        if precio_actual and self.peso_kg > 0:
            nuevo_valor = round(precio_actual.precio_venta / self.peso_kg, 2)
            
            if self.precio_por_unidad_medida != nuevo_valor:
                self.precio_por_unidad_medida = nuevo_valor
                Producto.objects.filter(pk=self.pk).update(precio_por_unidad_medida=nuevo_valor)

    def __str__(self):
        return self.nombre
            
        

# 4 MANEJO DE IMAGENES
class ImagenProducto(models.Model):
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE, 
        related_name='imagenes_galeria'
    )
    imagen = models.ImageField(upload_to='productos/galeria/')
    orden = models.PositiveIntegerField(default=0, help_text="Para decidir cuál va primero")

    class Meta:
        verbose_name = "Imagen de Galería"
        verbose_name_plural = "Galería de Imágenes"
        ordering = ['orden']

    def __str__(self):
        return f"Imagen para {self.producto.nombre}"

# 5. HISTORIAL DE PRECIOS
class HistorialPrecio(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='precios')
    
    # Mantenemos los nombres que usas en tu admin.py actual
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2)
    precio_costo = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True,   # <-- Permite que la DB acepte el valor vacío (NULL)
        blank=True   # <-- Permite que el formulario de Django pase la validación sin este dato
    )
    precio_oferta = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Campos extra estilo "Coto" si los necesitas (opcional, por ahora usamos los tuyos)
    precio_regular = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    precio_sin_impuestos = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    fecha_inicio = models.DateTimeField(auto_now_add=True)
    es_actual = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Historial de Precio"
        verbose_name_plural = "Historial de Precios"
        ordering = ['-fecha_inicio']

    def save(self, *args, **kwargs):
        if self.es_actual:
            HistorialPrecio.objects.filter(producto=self.producto, es_actual=True).exclude(pk=self.pk).update(es_actual=False)
        
        super().save(*args, **kwargs)
        
        # REFUERZO: Forzamos al producto a recalcular su unidad de medida
        if self.es_actual and self.producto.peso_kg > 0:
            valor_kilo = round(self.precio_venta / self.producto.peso_kg, 2)
            Producto.objects.filter(pk=self.producto.pk).update(precio_por_unidad_medida=valor_kilo)

    def __str__(self):
        return f"{self.producto.nombre} - ${self.precio_venta} ({self.fecha_inicio.date()})"

# 6. FAVORITOS
class Favorito(models.Model):
    usuario = models.ForeignKey('gestion_usuarios.Usuario', on_delete=models.CASCADE, related_name='favoritos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='favoritos_usuarios')
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'producto')
        verbose_name = "Favorito"
        verbose_name_plural = "Favoritos"

    def __str__(self):
        return f"{self.usuario.username} - {self.producto.nombre}"
