from .models import Categoria, Favorito

def lista_categorias(request):
    """
    Envía las categorías principales al menú desplegable de todas las páginas.
    """
    return {
        'categorias_padre': Categoria.objects.filter(padre__isnull=True, activa=True).order_by('orden', 'nombre')
    }

def favoritos_usuario(request):
    """
    Envía los IDs de los productos favoritos del usuario logueado.
    """
    if request.user.is_authenticated:
        ids = Favorito.objects.filter(usuario=request.user).values_list('producto_id', flat=True)
        return {'user_favoritos_ids': list(ids)}
    return {'user_favoritos_ids': []}