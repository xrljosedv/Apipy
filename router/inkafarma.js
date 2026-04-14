import requests
from bs4 import BeautifulSoup
import json
import time

def scrape_inkafarma_search(query):
    if not query or not isinstance(query, str):
        return {"status": False, "error": "Parámetro 'query' requerido"}

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-PE,es;q=0.9',
    }
    
    url = f"https://inkafarma.pe/search?q={requests.utils.quote(query)}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        productos = []
        
        items = soup.select('div[data-product-id]')
        
        if not items:
            items = soup.select('.product-item, .product, .item-product')

        for item in items[:10]:
            try:
                name_tag = item.select_one('.product-item-name, .name, .link, h3')
                nombre = name_tag.text.strip() if name_tag else "Nombre no disponible"
                
                price_tag = item.select_one('.price, .special-price, .regular-price, [class*="price"]')
                precio = price_tag.text.strip() if price_tag else "Precio no disponible"
                
                link_tag = item.select_one('a')
                enlace = link_tag.get('href') if link_tag else None
                if enlace and not enlace.startswith('http'):
                    enlace = f"https://inkafarma.pe{enlace}"
                
                img_tag = item.select_one('img')
                imagen = img_tag.get('src') if img_tag else None
                if imagen and imagen.startswith('//'):
                    imagen = f"https:{imagen}"

                productos.append({
                    "nombre": nombre,
                    "precio": precio,
                    "enlace": enlace,
                    "imagen": imagen
                })
                
            except Exception:
                continue
                
        return {
            "status": True,
            "query": query,
            "total": len(productos),
            "resultados": productos
        }
            
    except requests.exceptions.RequestException as e:
        return {"status": False, "error": f"Error de conexión: {str(e)}"}
    except Exception as e:
        return {"status": False, "error": f"Error procesando datos: {str(e)}"}

def run(ctx):
    req = ctx['req']
    query = req.get('query', {}).get('q', req.get('query', {}).get('query', ''))
    
    if not query:
        return {
            'status': False,
            'error': 'Parámetro requerido',
            'message': "Debes proporcionar 'q' o 'query' en la URL",
            'code': 400
        }
    
    start_time = time.time()
    data = scrape_inkafarma_search(query)
    data['tiempo_respuesta'] = f"{time.time() - start_time:.2f}s"
    
    return data

endpoints = [
    {
        'metode': 'GET',
        'endpoint': '/search/inkafarma',
        'name': 'Buscador de Productos Inkafarma',
        'category': 'Search',
        'description': 'Busca productos en Inkafarma.pe y devuelve nombre, precio y enlace.',
        'tags': ['Search', 'Farmacia', 'Peru', 'Precios'],
        'example': '?q=paracetamol',
        'parameters': [
            {
                'name': 'q',
                'in': 'query',
                'required': True,
                'schema': {'type': 'string'},
                'description': 'Término de búsqueda',
                'example': 'paracetamol',
            }
        ],
        'isPremium': False,
        'isMaintenance': False,
        'isPublic': True,
        'middleware': ['apiKey'],
        'run': run
    }
]
