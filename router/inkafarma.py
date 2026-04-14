import requests
from bs4 import BeautifulSoup
import json
import time
import re
import cloudscraper

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
    }
    
    try:
        scraper = cloudscraper.create_scraper()
        
        scraper.get("https://inkafarma.pe/", headers=headers, timeout=15)
        
        search_url = f"https://inkafarma.pe/{requests.utils.quote(query)}?_q={requests.utils.quote(query)}&map=ft"
        
        response = scraper.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        productos = []
        
        api_patterns = [
            r'"products":\s*(\[.*?\])',
            r'__STATE__\s*=\s*({.*?});',
            r'window\.__RUNTIME__\s*=\s*({.*?});',
        ]
        
        for pattern in api_patterns:
            match = re.search(pattern, response.text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, dict) and 'productName' in value:
                                nombre = value.get('productName', 'Nombre no disponible')
                                link = value.get('link', '')
                                if link and not link.startswith('http'):
                                    link = f"https://inkafarma.pe{link}"
                                
                                precio = 'Precio no disponible'
                                if 'items' in value:
                                    for item in value['items']:
                                        if 'sellers' in item:
                                            for seller in item['sellers']:
                                                if 'commertialOffer' in seller:
                                                    precio = f"S/ {seller['commertialOffer'].get('Price', 'Precio no disponible')}"
                                                    break
                                
                                productos.append({
                                    "nombre": nombre,
                                    "precio": precio,
                                    "enlace": link,
                                    "imagen": value.get('items', [{}])[0].get('images', [{}])[0].get('imageUrl', '') if 'items' in value else ''
                                })
                except:
                    pass
        
        if not productos:
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    match = re.search(r'fetch\("([^"]+)"\)', script.string)
                    if match:
                        api_url = match.group(1)
                        if 'search' in api_url or 'product' in api_url:
                            try:
                                if api_url.startswith('/'):
                                    api_url = f"https://inkafarma.pe{api_url}"
                                api_response = scraper.get(api_url, headers=headers, timeout=10)
                                if api_response.status_code == 200:
                                    api_data = api_response.json()
                                    for item in api_data[:10]:
                                        nombre = item.get('productName', item.get('name', 'Nombre no disponible'))
                                        precio = f"S/ {item.get('price', item.get('Price', 'Precio no disponible'))}"
                                        enlace = item.get('link', item.get('url', ''))
                                        if enlace and not enlace.startswith('http'):
                                            enlace = f"https://inkafarma.pe{enlace}"
                                        productos.append({
                                            "nombre": nombre,
                                            "precio": precio,
                                            "enlace": enlace,
                                            "imagen": item.get('image', item.get('imageUrl', ''))
                                        })
                            except:
                                pass
        
        if not productos:
            all_links = soup.find_all('a', href=True)
            product_links = []
            
            for link in all_links:
                href = link.get('href', '')
                if '/product/' in href or '/p/' in href or query.lower().replace(' ', '-') in href.lower():
                    if href not in product_links:
                        product_links.append(href)
            
            for link in product_links[:10]:
                try:
                    if not link.startswith('http'):
                        link = f"https://inkafarma.pe{link}"
                    
                    product_response = scraper.get(link, headers=headers, timeout=10)
                    product_soup = BeautifulSoup(product_response.text, 'html.parser')
                    
                    nombre_elem = product_soup.find('h1') or product_soup.find('h2', class_=re.compile(r'name|title', re.I))
                    nombre = nombre_elem.text.strip() if nombre_elem else query.capitalize()
                    
                    precio_elem = product_soup.find('span', class_=re.compile(r'price|Price|selling', re.I))
                    precio = precio_elem.text.strip() if precio_elem else 'Precio no disponible'
                    
                    img_elem = product_soup.find('img', class_=re.compile(r'product|main', re.I))
                    imagen = img_elem.get('src', '') if img_elem else ''
                    
                    productos.append({
                        "nombre": nombre,
                        "precio": precio,
                        "enlace": link,
                        "imagen": imagen
                    })
                except:
                    continue
        
        if not productos:
            fallback_urls = [
                f"https://inkafarma.pe/catalog_system/pub/products/search/{requests.utils.quote(query)}",
                f"https://inkafarma.pe/api/catalog_system/pub/products/search?ft={requests.utils.quote(query)}",
                f"https://inkafarma.pe/api/catalog_system/pub/products/search/{requests.utils.quote(query)}?sc=1"
            ]
            
            for url in fallback_urls:
                try:
                    api_response = scraper.get(url, headers=headers, timeout=10)
                    if api_response.status_code == 200:
                        data = api_response.json()
                        for item in data[:10]:
                            nombre = item.get('productName', item.get('name', 'Nombre no disponible'))
                            precio = 'Precio no disponible'
                            if 'items' in item and item['items']:
                                sellers = item['items'][0].get('sellers', [])
                                if sellers and 'commertialOffer' in sellers[0]:
                                    precio = f"S/ {sellers[0]['commertialOffer'].get('Price', 'Precio no disponible')}"
                            
                            enlace = item.get('link', '')
                            if enlace and not enlace.startswith('http'):
                                enlace = f"https://inkafarma.pe{enlace}"
                            
                            imagen = ''
                            if 'items' in item and item['items']:
                                images = item['items'][0].get('images', [])
                                if images:
                                    imagen = images[0].get('imageUrl', '')
                            
                            productos.append({
                                "nombre": nombre,
                                "precio": precio,
                                "enlace": enlace,
                                "imagen": imagen
                            })
                        if productos:
                            break
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
