import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import quote, urlparse, parse_qs
import random
from http.cookiejar import LWPCookieJar
import ssl
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import cloudscraper
    _CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    _CLOUDSCRAPER_AVAILABLE = False

try:
    from lxml import etree
    _LXML_AVAILABLE = True
except ImportError:
    _LXML_AVAILABLE = False

def create_session():
    session = requests.Session()
    session.cookies = LWPCookieJar()
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'es-PE,es;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Ch-Ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    })
    return session

def fallback_cloudscraper_get(url, timeout=15):
    if _CLOUDSCRAPER_AVAILABLE:
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        return scraper.get(url, timeout=timeout, verify=False)
    return None

def scrape_inkafarma_search(query):
    if not query or not isinstance(query, str):
        return {"status": False, "error": "Parámetro 'query' requerido"}

    session = create_session()
    productos = []
    headers_api = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://www.inkafarma.pe',
        'Referer': 'https://www.inkafarma.pe/',
        'Sec-Fetch-Site': 'same-origin',
    }

    def extract_from_api_response(data):
        items = []
        if not data:
            return items
        if isinstance(data, dict):
            source = data.get('products', data.get('data', data))
        else:
            source = data
        if not isinstance(source, list):
            return items
        for item in source[:20]:
            nombre = item.get('productName') or item.get('name') or item.get('producto') or item.get('title') or 'Nombre no disponible'
            precio = 'Precio no disponible'
            enlace = ''
            imagen = ''

            items_list = item.get('items', [])
            if items_list:
                sellers = items_list[0].get('sellers', [])
                if sellers:
                    offer = sellers[0].get('commertialOffer', {})
                    price = offer.get('Price')
                    if price is not None:
                        try:
                            precio = f"S/ {float(price):.2f}"
                        except:
                            precio = f"S/ {price}"
                images = items_list[0].get('images', [])
                if images:
                    imagen = images[0].get('imageUrl', '')
            else:
                price_raw = item.get('price') or item.get('Price') or item.get('precio')
                if price_raw is not None:
                    try:
                        precio = f"S/ {float(price_raw):.2f}"
                    except:
                        precio = f"S/ {price_raw}"
                imagen = item.get('image') or item.get('imagen') or item.get('thumbnail') or ''

            enlace = item.get('link') or item.get('linkText') or item.get('url') or ''
            if enlace:
                if not enlace.startswith('http'):
                    if enlace.startswith('/'):
                        enlace = f"https://www.inkafarma.pe{enlace}"
                    else:
                        enlace = f"https://www.inkafarma.pe/{enlace}/p"
            items.append({
                "nombre": nombre.strip() if isinstance(nombre, str) else str(nombre),
                "precio": precio,
                "enlace": enlace,
                "imagen": imagen
            })
        return items

    def try_api_endpoint(url):
        try:
            resp = session.get(url, headers=headers_api, timeout=10)
            if resp.status_code == 200:
                return extract_from_api_response(resp.json())
        except:
            pass
        return []

    def try_html_parsing(url):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, 'html.parser')
            scripts = soup.find_all('script')
            state_data = None
            for script in scripts:
                if script.string and '__STATE__' in script.string:
                    match = re.search(r'__STATE__\s*=\s*({.*?});', script.string, re.DOTALL)
                    if match:
                        try:
                            state_data = json.loads(match.group(1))
                            break
                        except:
                            continue
            if state_data:
                prods = []
                for key, val in state_data.items():
                    if isinstance(val, dict) and 'productName' in val and 'productId' in val:
                        nombre = val.get('productName', 'Nombre no disponible')
                        precio = 'Precio no disponible'
                        if 'priceRange' in val:
                            precio = val['priceRange'].get('sellingPrice', {}).get('highPrice', 'Precio no disponible')
                        enlace = val.get('linkText', '')
                        if enlace:
                            enlace = f"https://www.inkafarma.pe/{enlace}/p"
                        imagen = ''
                        items_list = val.get('items', [])
                        if items_list:
                            images = items_list[0].get('images', [])
                            if images:
                                imagen = images[0].get('imageUrl', '')
                        prods.append({
                            "nombre": nombre,
                            "precio": f"S/ {precio}" if precio != 'Precio no disponible' else precio,
                            "enlace": enlace,
                            "imagen": imagen
                        })
                if prods:
                    return prods

            product_cards = soup.select('div.vtex-search-result-3-x-galleryItem, div[data-testid="product-item"], a[href*="/product/"], a[href*="/p/"]')
            seen = set()
            html_prods = []
            for card in product_cards[:20]:
                link_tag = card if card.name == 'a' else card.find('a')
                if not link_tag:
                    continue
                enlace = link_tag.get('href')
                if not enlace or enlace in seen:
                    continue
                if not enlace.startswith('http'):
                    enlace = f"https://www.inkafarma.pe{enlace}"
                seen.add(enlace)

                nombre_tag = card.find('h2') or card.find('h3') or card.find('span', class_=re.compile(r'name|title|product-name', re.I))
                nombre = nombre_tag.get_text(strip=True) if nombre_tag else 'Nombre no disponible'

                precio_tag = card.find('span', class_=re.compile(r'price|Price|currency', re.I)) or card.find('div', class_=re.compile(r'price', re.I))
                precio = precio_tag.get_text(strip=True) if precio_tag else 'Precio no disponible'

                img_tag = card.find('img')
                imagen = img_tag.get('src') or img_tag.get('data-src') or ''

                html_prods.append({
                    "nombre": nombre,
                    "precio": precio,
                    "enlace": enlace,
                    "imagen": imagen
                })
            return html_prods
        except:
            return []

    endpoints_to_try = [
        f"https://www.inkafarma.pe/api/io/_v/api/intelligent-search/product_search/*{quote(query)}?page=1&count=20",
        f"https://www.inkafarma.pe/api/catalog_system/pub/products/search/{quote(query)}?sc=1",
        f"https://www.inkafarma.pe/api/catalog_system/pub/products/search?ft={quote(query)}",
        f"https://www.inkafarma.pe/api/catalog_system/pub/products/search?fq={quote(query)}",
        f"https://www.inkafarma.pe/api/catalog_system/pub/products/search?map=ft&_q={quote(query)}",
        f"https://www.inkafarma.pe/_v/api/intelligent-search/product_search?query={quote(query)}&page=1&count=20",
    ]

    for ep in endpoints_to_try:
        productos = try_api_endpoint(ep)
        if productos:
            break

    if not productos:
        search_url = f"https://www.inkafarma.pe/{quote(query)}?_q={quote(query)}&map=ft"
        productos = try_html_parsing(search_url)

    if not productos:
        fallback_url = f"https://www.inkafarma.pe/buscar?q={quote(query)}"
        productos = try_html_parsing(fallback_url)

    if not productos:
        search_page_url = f"https://www.inkafarma.pe/s/{quote(query)}"
        productos = try_html_parsing(search_page_url)

    if not productos and _CLOUDSCRAPER_AVAILABLE:
        try:
            cloud_resp = fallback_cloudscraper_get(f"https://www.inkafarma.pe/buscar?q={quote(query)}", timeout=15)
            if cloud_resp and cloud_resp.status_code == 200:
                soup = BeautifulSoup(cloud_resp.text, 'html.parser')
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and '__STATE__' in script.string:
                        match = re.search(r'__STATE__\s*=\s*({.*?});', script.string, re.DOTALL)
                        if match:
                            try:
                                state = json.loads(match.group(1))
                                for val in state.values():
                                    if isinstance(val, dict) and 'productName' in val:
                                        nombre = val.get('productName', '')
                                        precio = 'Precio no disponible'
                                        enlace = val.get('linkText', '')
                                        if enlace:
                                            enlace = f"https://www.inkafarma.pe/{enlace}/p"
                                        productos.append({
                                            "nombre": nombre,
                                            "precio": precio,
                                            "enlace": enlace,
                                            "imagen": ""
                                        })
                            except:
                                pass
        except:
            pass

    return {
        "status": True if productos else False,
        "query": query,
        "total": len(productos),
        "resultados": productos
    }

def run(ctx):
    req = ctx.get('req', {})
    query_params = req.get('query', {})
    query = query_params.get('q') or query_params.get('query') or ''
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
