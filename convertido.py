def transformar_a_html(texto_plano):
    lineas = texto_plano.strip().split('\n')
    html_resultado = []
    en_lista = False

    for i, linea in enumerate(lineas):
        linea = linea.strip()
        if not linea:
            continue

        # 1. Detectar si la línea debe ser un ítem de lista (empieza con un punto o guion)
        if linea.startswith('Pantalla') or linea.startswith('Smart TV') or linea.startswith('Diseño'):
            if not en_lista:
                html_resultado.append("<ul>")
                en_lista = True
            html_resultado.append(f"    <li>{linea}</li>")
        
        else:
            # Si veníamos de una lista y la línea actual no lo es, cerramos la lista
            if en_lista:
                html_resultado.append("</ul>")
                en_lista = False
            
            # 2. Lógica para Negritas (Primera línea o títulos específicos)
            if i == 0 or "Por qué elegir" in linea:
                html_resultado.append(f"<p><b>{linea}</b></p>")
            else:
                # 3. Párrafo común
                html_resultado.append(f"<p>{linea}</p>")

    # Cerrar la lista si quedó abierta al final
    if en_lista:
        html_resultado.append("</ul>")

    return "\n".join(html_resultado)

# El texto de entrada
texto = """Tv Led 58" Smart Db58X7500 Noblex
Transformá tu experiencia de entretenimiento con el televisor Noblex. Con su pantalla LED de 58" y tecnología Smart, vas a disfrutar de imágenes nítidas y una navegación fluida.
Porque elegir Tv Led 58" Smart Db58X7500 Noblex
Pantalla LED de 58" para una experiencia visual única.
Smart TV con acceso a tus aplicaciones favoritas.
Resolución Full HD para imágenes claras y detalles precisos.
Diseño elegante que se adapta perfectamente a tu casa.
Vas a disfrutar de tus series, películas y deportes favoritos como nunca antes. Compralo ahora con envío a domicilio o retiro en tienda."""

# Ejecución
resultado = transformar_a_html(texto)
print(resultado)