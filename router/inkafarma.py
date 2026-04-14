import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import quote

def scrape_inkafarma_search(query):
    if not query or not isinstance(query, str):
        return {"status": False, "error": "Parámetro 'query' requerido"}

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'es-PE,es;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Referer': 'https://www.inkafarma.pe/',
    }

    productos = []
    session = requests.Session()
    session.headers.update(headers)

    def extract_products(data_list):
        items = []
        for item in data_list[:20]:
            nombre = item.get('productName') or item.get('name') or 'Nombre no disponible'
            precio = 'Precio no disponible'
            items_list = item.get('items', [])
            if items_list:
                sellers = items_list[0].get('sellers', [])
                if sellers:
                    offer = sellers[0].get('commertialOffer', {})
                    price = offer.get('Price')
                    if price is not None:
                        precio = f"S/ {price:.2f}" if isinstance(price, (int, float)) else f"S/ {price}"
            enlace = item.get('link', '')
            if enlace and not enlace.startswith('http'):
                enlace = f"https://www.inkafarma.pe{enlace}"
            imagen = ''
            if items_list:
                images = items_list[0].get('images', [])
                if images:
                    imagen = images[0].get('imageUrl', '')
            items.append({
                "nombre": nombre,
                "precio": precio,
                "enlace": enlace,
                "imagen": imagen
            })
        return items

    try:
        api_url = f"https://www.inkafarma.pe/api/catalog_system/pub/products/search?ft={quote(query)}"
        resp = session.get(api_url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                productos = extract_products(data)
    except:
        pass

    if not productos:
        try:
            alt_api = f"https://www.inkafarma.pe/api/catalog_system/pub/products/search/{quote(query)}?sc=1"
            resp = session.get(alt_api, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    productos = extract_products(data)
        except:
            pass

    if not productos:
        try:
            search_url = f"https://www.inkafarma.pe/{quote(query)}?_q={quote(query)}&map=ft"
            resp = session.get(search_url, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    match = re.search(r'__STATE__\s*=\s*({.*?});', script.string, re.DOTALL)
                    if match:
                        try:
                            state = json.loads(match.group(1))
                            for key, val in state.items():
                                if isinstance(val, dict) and 'productName' in val:
                                    nombre = val.get('productName', 'Nombre no disponible')
                                    precio = 'Precio no disponible'
                                    items_list = val.get('items', [])
                                    if items_list:
                                        sellers = items_list[0].get('sellers', [])
                                        if sellers:
                                            offer = sellers[0].get('commertialOffer', {})
                                            price = offer.get('Price')
                                            if price is not None:
                                                precio = f"S/ {price:.2f}" if isinstance(price, (int, float)) else f"S/ {price}"
                                    enlace = val.get('link', '')
                                    if enlace and not enlace.startswith('http'):
                                        enlace = f"https://www.inkafarma.pe{enlace}"
                                    imagen = ''
                                    if items_list:
                                        images = items_list[0].get('images', [])
                                        if images:
                                            imagen = images[0].get('imageUrl', '')
                                    productos.append({
                                        "nombre": nombre,
                                        "precio": precio,
                                        "enlace": enlace,
                                        "imagen": imagen
                                    })
                        except:
                            pass
        except:
            pass

    if not productos:
        try:
            search_page = f"https://www.inkafarma.pe/buscar?q={quote(query)}"
            resp = session.get(search_page, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            product_cards = soup.find_all('a', href=re.compile(r'/(producto|product)/'))
            seen = set()
            for card in product_cards[:15]:
                enlace = card.get('href')
                if not enlace:
                    continue
                if not enlace.startswith('http'):
                    enlace = f"https://www.inkafarma.pe{enlace}"
                if enlace in seen:
                    continue
                seen.add(enlace)
                nombre_tag = card.find('h2') or card.find('h3') or card.find('span', class_=re.compile(r'name|title', re.I))
                nombre = nombre_tag.text.strip() if nombre_tag else query
                precio_tag = card.find('span', class_=re.compile(r'price|Price', re.I))
                precio = precio_tag.text.strip() if precio_tag else 'Precio no disponible'
                img_tag = card.find('img')
                imagen = img_tag.get('src') or img_tag.get('data-src') or ''
                productos.append({
                    "nombre": nombre,
                    "precio": precio,
                    "enlace": enlace,
                    "imagen": imagen
                })
        except:
            pass

    return {
        "status": True if productos else False,
        "query": query,
        "total": len(productos),
        "resultados": productos
    }

def run(ctx):
    req = ctx['req']
    query = req.get('query', {}).get('q') or req.get('query', {}).get('query') or ''
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
