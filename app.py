import os
import importlib
import pkgutil
import asyncio
import datetime
from flask import Flask, render_template, send_from_directory, request, jsonify, Response
from flask_cors import CORS
import pathlib

app = Flask(__name__)
CORS(app)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

PORT = int(os.environ.get('PORT', 8000))
ROUTER_DIR = pathlib.Path(__file__).parent / 'router'

_endpoints_cache = None

def load_routers():
    if not ROUTER_DIR.exists():
        print(f"\u26a0\ufe0f Carpeta 'router' no encontrada en {ROUTER_DIR}")
        return

    init_file = ROUTER_DIR / '__init__.py'
    if not init_file.exists():
        init_file.touch()

    for module_info in pkgutil.iter_modules([str(ROUTER_DIR)]):
        if module_info.name.startswith('_'):
            continue
        try:
            module = importlib.import_module(f'router.{module_info.name}')
            endpoints = getattr(module, 'endpoints', None)
            if not endpoints:
                print(f"\u26a0\ufe0f El módulo router.{module_info.name} no define 'endpoints'")
                continue

            for endpoint_def in endpoints:
                register_endpoint(endpoint_def)
        except Exception as e:
            print(f"\u274c Error cargando router.{module_info.name}: {e}")

def register_endpoint(ep):
    path = ep.get('endpoint')
    method = ep.get('metode', 'GET').upper()
    name = ep.get('name', path)

    if not path:
        print(f"\u26a0\ufe0f Endpoint sin 'endpoint': {ep}")
        return

    async def handler(**kwargs):
        req = {
            'query': request.args,
            'params': request.view_args,
            'body': request.get_json(silent=True) if request.is_json else request.form,
            'headers': dict(request.headers),
            'method': request.method,
            'files': request.files
        }
        res = {
            'status': lambda code: None,
            'set': lambda key, value: None,
            'send': lambda data: data,
            'json': lambda data: data,
            'end': lambda data=None: data
        }

        try:
            result = ep['run']({'req': req, 'res': res})
            if result is not None:
                if isinstance(result, dict) and 'status' in result:
                    code = result.get('code', 200)
                    response_data = {k: v for k, v in result.items() if k != 'code'}
                    return jsonify(response_data), code
                else:
                    return jsonify(result)
            return Response(status=204)
        except Exception as e:
            print(f"Error en endpoint {path}: {e}")
            return jsonify({
                'status': False,
                'creator': 'Xrljose Xxdv\u308f',
                'error': str(e),
                'code': 500
            }), 500

    def sync_handler(*args, **kwargs):
        return asyncio.run(handler(*args, **kwargs))

    app.add_url_rule(
        path,
        endpoint=name,
        view_func=sync_handler,
        methods=[method]
    )
    print(f"\u2705 Registrado {method} {path} -> {name}")

@app.route('/style.css')
def serve_style():
    return send_from_directory('static', 'style.css')

@app.route('/script.js')
def serve_script():
    return send_from_directory('static', 'script.js')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/docs')
def docs():
    return render_template('docs.html')

@app.route('/category')
@app.route('/category/<name>')
def category(name=None):
    return render_template('category.html')

@app.route('/support')
def support():
    return render_template('support.html')

def get_all_endpoints():
    endpoints = []
    if ROUTER_DIR.exists():
        for module_info in pkgutil.iter_modules([str(ROUTER_DIR)]):
            try:
                module = importlib.import_module(f'router.{module_info.name}')
                eps = getattr(module, 'endpoints', [])
                for ep in eps:
                    endpoints.append({
                        'name': ep.get('name', ep.get('endpoint')),
                        'endpoint': ep.get('endpoint'),
                        'method': ep.get('metode', 'GET'),
                        'category': ep.get('category', 'General'),
                        'description': ep.get('description', 'Sin descripción'),
                        'parameters': ep.get('parameters', []),
                        'supportsUpload': ep.get('supportsUpload', False)
                    })
            except Exception:
                continue
    return endpoints

@app.route('/api/list')
def api_list():
    try:
        eps = get_all_endpoints()
        return jsonify({
            'status': True,
            'creator': 'Xrljose Xxdv\u308f',
            'data': eps,
            'count': len(eps),
            'timestamp': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': False,
            'creator': 'Xrljose Xxdv\u308f',
            'error': str(e),
            'code': 500
        }), 500

@app.route('/api/ip')
def api_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        ip = forwarded.split(',')[0].strip()
    else:
        ip = request.remote_addr
    return jsonify({
        'status': True,
        'creator': 'Xrljose Xxdv\u308f',
        'ip': ip,
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({
            'status': False,
            'creator': 'Xrljose Xxdv\u308f',
            'error': 'Endpoint not found',
            'code': 404
        }), 404
    return render_template('index.html'), 404

if __name__ == '__main__':
    print("\033[34m\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\033[0m")
    print("\033[34m\u2551\033[0m              \033[37mXdvxrlru.zz API Server (Python)\033[0m                 \033[34m\u2551\033[0m")
    print("\033[34m\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\033[0m")
    print("\033[32m\u2713\033[0m Servidor iniciado correctamente")
    print("\033[36m\U0001F464\033[0m Creador: Xrljose Xxdv\u308f")
    print()
    print(f"\033[34m\u25ba\033[0m Servidor: \033[36mhttp://localhost:{PORT}\033[0m")
    print(f"\033[34m\u25ba\033[0m Documentación: \033[36mhttp://localhost:{PORT}/docs\033[0m")
    print(f"\033[34m\u25ba\033[0m Categorías: \033[36mhttp://localhost:{PORT}/category\033[0m")
    print(f"\033[34m\u25ba\033[0m Support: \033[36mhttp://localhost:{PORT}/support\033[0m")
    print(f"\033[34m\u25ba\033[0m API List: \033[36mhttp://localhost:{PORT}/api/list\033[0m")
    
    load_routers()
    app.run(host='0.0.0.0', port=PORT, debug=False)