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
texto = """Smart TV 55" Crystal UHD DU7000 UN55DU7000GCZB Samsung
Transformá tu living en un cine con imágenes ultra nítidas...
Por qué elegir el Smart TV 55":
Pantalla de 55" Crystal UHD para detalles impresionantes.
Smart TV con acceso a tus apps favoritas.
Diseño delgado y moderno.
Viví cada escena como nunca..."""

# Ejecución
resultado = transformar_a_html(texto)
print(resultado)