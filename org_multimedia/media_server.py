import threading
import bottle
from pathlib import Path

# Configuramos un pequeño servidor web interno
media_app = bottle.Bottle()

@media_app.route('/media')
def serve_media():
    path_str = bottle.request.query.path
    if not path_str:
        return bottle.HTTPError(400, "Parámetro 'path' requerido")
    
    p = Path(path_str).resolve()
    if not p.is_file():
        return bottle.HTTPError(404, "Archivo no encontrado")
    
    # bottle.static_file maneja automáticamente las peticiones de rango (Range headers)
    # que son cruciales para el streaming de video
    return bottle.static_file(p.name, root=str(p.parent))

# Añadimos cabeceras CORS para evitar bloqueos del navegador embebido
@media_app.hook('after_request')
def enable_cors():
    bottle.response.headers['Access-Control-Allow-Origin'] = '*'
    bottle.response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    bottle.response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

def start_media_server(port=51234):
    """Arranca el servidor de medios en un hilo daemon."""
    def _run():
        bottle.run(app=media_app, host='127.0.0.1', port=port, quiet=True)
    
    t = threading.Thread(target=_run, daemon=True)
    t.start()
