class TicketMostrador:
    def __init__(self, request):
        self.session = request.session
        ticket = self.session.get("ticket_mostrador")
        if not ticket:
            ticket = self.session["ticket_mostrador"] = {}
        self.ticket = ticket

    def agregar(self, producto):
        p_id = str(producto.id)
        # Buscamos el precio actual
        precio_obj = producto.precios.filter(es_actual=True).first()
        precio = float(precio_obj.precio_venta) if precio_obj else 0.0

        if p_id not in self.ticket:
            self.ticket[p_id] = {
                "producto_id": producto.id,
                "nombre": str(producto.nombre),
                "sku": str(producto.sku),
                "precio": precio,
                "cantidad": 1,
                "acumulado": precio
            }
        else:
            self.ticket[p_id]["cantidad"] += 1
            self.ticket[p_id]["acumulado"] = self.ticket[p_id]["cantidad"] * precio
        self.guardar()

    def restar(self, producto_id):
        p_id = str(producto_id)
        if p_id in self.ticket:
            self.ticket[p_id]["cantidad"] -= 1
            if self.ticket[p_id]["cantidad"] <= 0:
                del self.ticket[p_id]
            else:
                self.ticket[p_id]["acumulado"] = self.ticket[p_id]["cantidad"] * self.ticket[p_id]["precio"]
            self.guardar()

    def guardar(self):
        self.session["ticket_mostrador"] = self.ticket
        self.session.modified = True

    def limpiar(self):
        self.session["ticket_mostrador"] = {}
        self.session.modified = True

    def get_total(self):
        return sum(item["acumulado"] for item in self.ticket.values())