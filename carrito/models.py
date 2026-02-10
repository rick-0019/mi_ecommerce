from decimal import Decimal

class Carrito:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        carrito = self.session.get("carrito")
        if not carrito:
            carrito = self.session["carrito"] = {}
        self.carrito = carrito

    def agregar(self, producto):
        id = str(producto.id)
        
        # Obtenemos el precio actual desde la relación 'precios' de tu modelo HistorialPrecio
        precio_obj = producto.precios.filter(es_actual=True).first()
        
        # Si no hay precio marcado como actual, podrías usar un valor por defecto o 0
        valor_venta = float(precio_obj.precio_venta) if precio_obj else 0.0

        if id not in self.carrito:
            self.carrito[id] = {
                "producto_id": producto.id,
                "nombre": producto.nombre,
                "sku": producto.sku,
                "precio": valor_venta, 
                "cantidad": 1,
                "acumulado": valor_venta,
                "imagen": producto.imagen_principal.url if producto.imagen_principal else ""
            }
        else:
            self.carrito[id]["cantidad"] += 1
            self.carrito[id]["acumulado"] += valor_venta
        
        self.guardar_carrito()

    def guardar_carrito(self):
        self.session["carrito"] = self.carrito
        self.session.modified = True

    def eliminar(self, producto):
        id = str(producto.id)
        if id in self.carrito:
            del self.carrito[id]
            self.guardar_carrito()

    def restar(self, producto):
        id = str(producto.id)
        if id in self.carrito:
            # Buscamos el precio para restar correctamente el acumulado
            precio_obj = producto.precios.filter(es_actual=True).first()
            valor_venta = float(precio_obj.precio_venta) if precio_obj else 0.0
            
            self.carrito[id]["cantidad"] -= 1
            self.carrito[id]["acumulado"] -= valor_venta
            
            if self.carrito[id]["cantidad"] <= 0:
                self.eliminar(producto)
            else:
                self.guardar_carrito()

    def limpiar(self):
        self.session["carrito"] = {}
        self.session.modified = True

# Create your models here.
