import requests
from bs4 import BeautifulSoup
import json
import time
import re

def scrape_inkafarma_search(query):
    if not query or not isinstance(query, str):
        return {"status": False, "error": "Parámetro 'query' requerido"}

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'es-PE,es;q=0.9',
        'Referer': 'https://inkafarma.pe/',
        'Origin': 'https://inkafarma.pe',
    }
    
    search_url = f"https://inkafarma.pe/search?q={requests.utils.quote(query)}"
    
    try:
        session = requests.Session()
        session.get("https://inkafarma.pe/", headers=headers, timeout=10)
        
        response = session.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        productos = []
        
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if '@graph' in data:
                    for item in data['@graph']:
                        if item.get('@type') == 'Product':
                            nombre = item.get('name', 'Nombre no disponible')
                            precio = item.get('offers', {}).get('price', 'Precio no disponible')
                            enlace = item.get('url', '')
                            imagen = item.get('image', '')
                            
                            productos.append({
                                "nombre": nombre,
                                "precio": f"S/ {precio}" if precio != 'Precio no disponible' else precio,
                                "enlace": enlace,
                                "imagen": imagen
                            })
            except:
                pass
        
        if not productos:
            product_cards = soup.select('article[data-testid="product-card"], div[class*="product"], div[class*="ProductCard"], li[class*="product"]')
            
            for card in product_cards[:10]:
                try:
                    name_elem = card.find(['h2', 'h3', 'p', 'span'], class_=re.compile(r'name|title|description', re.I))
                    nombre = name_elem.text.strip() if name_elem else "Nombre no disponible"
                    
                    price_elem = card.find(['span', 'p', 'div'], class_=re.compile(r'price|Price', re.I))
                    precio = price_elem.text.strip() if price_elem else "Precio no disponible"
                    
                    link_elem = card.find('a', href=True)
                    enlace = link_elem['href'] if link_elem else ''
                    if enlace and not enlace.startswith('http'):
                        enlace = f"https://inkafarma.pe{enlace}"
                    
                    img_elem = card.find('img')
                    imagen = img_elem.get('src') or img_elem.get('data-src', '') if img_elem else ''
                    
                    productos.append({
                        "nombre": nombre,
                        "precio": precio,
                        "enlace": enlace,
                        "imagen": imagen
                    })
                except:
                    continue
        
        if not productos:
            api_url = "https://inkafarma.pe/api/catalog_system/pub/products/search"
            params = {
                '_q': query,
                'map': 'ft',
                'sc': '1'
            }
            
            api_response = session.get(api_url, params=params, headers=headers, timeout=15)
            if api_response.status_code == 200:
                api_data = api_response.json()
                for item in api_data[:10]:
                    productos.append({
                        "nombre": item.get('productName', 'Nombre no disponible'),
                        "precio": f"S/ {item.get('items', [{}])[0].get('sellers', [{}])[0].get('commertialOffer', {}).get('Price', 'Precio no disponible')}",
                        "enlace": item.get('link', ''),
                        "imagen": item.get('items', [{}])[0].get('images', [{}])[0].get('imageUrl', '')
                    })
        
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
