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
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-PE,es;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    
    search_url = f"https://inkafarma.pe/search?q={requests.utils.quote(query)}"
    
    try:
        session = requests.Session()
        
        session.get("https://inkafarma.pe/", headers=headers, timeout=15)
        
        response = session.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        productos = []
        
        pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
        match = re.search(pattern, response.text, re.DOTALL)
        
        if match:
            try:
                data = json.loads(match.group(1))
                
                if 'search' in data and 'products' in data['search']:
                    for item in data['search']['products'][:10]:
                        nombre = item.get('productName', 'Nombre no disponible')
                        
                        price = 'Precio no disponible'
                        if 'items' in item and len(item['items']) > 0:
                            sellers = item['items'][0].get('sellers', [])
                            if sellers and 'commertialOffer' in sellers[0]:
                                price = f"S/ {sellers[0]['commertialOffer'].get('Price', 'Precio no disponible')}"
                        
                        enlace = item.get('link', '')
                        if enlace and not enlace.startswith('http'):
                            enlace = f"https://inkafarma.pe{enlace}"
                        
                        imagen = ''
                        if 'items' in item and len(item['items']) > 0:
                            images = item['items'][0].get('images', [])
                            if images:
                                imagen = images[0].get('imageUrl', '')
                        
                        productos.append({
                            "nombre": nombre,
                            "precio": price,
                            "enlace": enlace,
                            "imagen": imagen
                        })
            except json.JSONDecodeError:
                pass
        
        if not productos:
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
            soup = BeautifulSoup(response.text, 'html.parser')
            
            selectors = [
                'div.vtex-search-result-3-x-galleryItem',
                'section.vtex-product-summary-2-x-container',
                'div[class*="product"]',
                'article[class*="product"]',
                'div[class*="ProductCard"]',
                'li[class*="product"]'
            ]
            
            product_cards = []
            for selector in selectors:
                product_cards = soup.select(selector)
                if product_cards:
                    break
            
            for card in product_cards[:10]:
                try:
                    name_selectors = ['h2', 'h3', 'span[class*="name"]', 'span[class*="Name"]', 'p[class*="name"]', 'a[class*="name"]']
                    nombre = "Nombre no disponible"
                    for sel in name_selectors:
                        elem = card.select_one(sel)
                        if elem:
                            nombre = elem.text.strip()
                            break
                    
                    price_selectors = ['span[class*="price"]', 'span[class*="Price"]', 'div[class*="price"]', 'span[class*="sellingPrice"]']
                    precio = "Precio no disponible"
                    for sel in price_selectors:
                        elem = card.select_one(sel)
                        if elem:
                            precio = elem.text.strip()
                            break
                    
                    link_elem = card.find('a', href=True)
                    enlace = ''
                    if link_elem:
                        enlace = link_elem['href']
                        if not enlace.startswith('http'):
                            enlace = f"https://inkafarma.pe{enlace}"
                    
                    img_elem = card.find('img')
                    imagen = ''
                    if img_elem:
                        imagen = img_elem.get('src') or img_elem.get('data-src', '')
                    
                    if nombre != "Nombre no disponible":
                        productos.append({
                            "nombre": nombre,
                            "precio": precio,
                            "enlace": enlace,
                            "imagen": imagen
                        })
                except:
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
