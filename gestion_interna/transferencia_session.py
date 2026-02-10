class CarritoTransferencia:
    def __init__(self, request):
        self.session = request.session
        carrito = self.session.get('transferencia_cart')
        if not carrito:
            carrito = self.session['transferencia_cart'] = {}
        self.carrito = carrito

    def agregar(self, producto, cantidad=1):
        producto_id = str(producto.id)
        if producto_id not in self.carrito:
            self.carrito[producto_id] = {
                'producto_id': producto.id,
                'nombre': producto.nombre,
                'sku': producto.sku,
                'cantidad': cantidad,
            }
        else:
            self.carrito[producto_id]['cantidad'] += cantidad
        self.guardar()

    def restar(self, producto_id):
        producto_id = str(producto_id)
        if producto_id in self.carrito:
            self.carrito[producto_id]['cantidad'] -= 1
            if self.carrito[producto_id]['cantidad'] <= 0:
                self.eliminar(producto_id)
            self.guardar()

    def eliminar(self, producto_id):
        producto_id = str(producto_id)
        if producto_id in self.carrito:
            del self.carrito[producto_id]
            self.guardar()

    def limpiar(self):
        self.session['transferencia_cart'] = {}
        self.guardar()

    def guardar(self):
        self.session.modified = True