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
        if id not in self.carrito.keys():
            # Obtenemos el precio ejecutando el método con ()
            precio_valor = producto.precio_actual()

            self.carrito[id] = {
                "producto_id": producto.id,
                "sku": producto.sku,
                "nombre": producto.nombre,
                "precio": str(precio_valor),  # Agregados ()
                "cantidad": 1,
                "imagen": producto.imagen_principal.url if producto.imagen_principal else "",
                "acumulado": str(precio_valor),  # Agregados ()
            }
        else:
            for key, value in self.carrito.items():
                if key == str(producto.id):
                    value["cantidad"] += 1
                    # Agregados () en producto.precio_actual()
                    nuevo_acumulado = float(
                        value["acumulado"]) + float(producto.precio_actual())
                    value["acumulado"] = str(nuevo_acumulado)
                    break
        self.guardar_carrito()

    def guardar_carrito(self):
        self.session["carrito"] = self.carrito
        self.session.modified = True

    def eliminar(self, producto):
        producto_id = str(producto.id)
        if producto_id in self.carrito:
            del self.carrito[producto_id]
            self.guardar_carrito()

    def restar_producto(self, producto):
        producto_id = str(producto.id)
        for key, value in self.carrito.items():
            if key == producto_id:
                value["cantidad"] -= 1
                value["acumulado"] = float(
                    value["acumulado"]) - float(value["precio"])
                if value["cantidad"] < 1:
                    self.eliminar(producto)
                break
        self.guardar_carrito()

    def limpiar_carrito(self):
        self.session["carrito"] = {}
        self.session.modified = True

    # ... asegúrate de tener también eliminar, restar y limpiar ...
