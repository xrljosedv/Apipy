import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urlparse, parse_qs

# ============================================================
# SCRAPER PRINCIPAL
# ============================================================

def scrape_labpsych(video_url, format_preference=None):
    """
    Extrae enlaces de descarga de labpsych.pl (YTMP3/YTMP4)
    
    Args:
        video_url (str): URL completa del video de YouTube
        format_preference (str, opcional): 'mp3' o 'mp4' para filtrar resultado
    
    Returns:
        dict: {
            'status': bool,
            'video_id': str,
            'title': str,
            'formats': [
                {
                    'type': 'mp3'/'mp4',
                    'quality': str,
                    'url': str,
                    'size': str (opcional)
                }
            ],
            'error': str (si status=False)
        }
    """
    if not video_url:
        return {"status": False, "error": "URL de YouTube requerida"}

    # Extraer ID del video
    video_id = extract_youtube_id(video_url)
    if not video_id:
        return {"status": False, "error": "URL de YouTube inválida"}

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://labpsych.pl/',
        'Origin': 'https://labpsych.pl'
    })

    try:
        # 1. Obtener página principal para cookies y token CSRF (si existe)
        main_page = session.get('https://labpsych.pl/', timeout=15)
        soup_main = BeautifulSoup(main_page.text, 'html.parser')
        
        # Buscar token CSRF en meta o input hidden (común en algunos sitios)
        csrf_token = None
        token_input = soup_main.find('input', {'name': '_token'}) or \
                      soup_main.find('input', {'name': 'csrf_token'})
        if token_input:
            csrf_token = token_input.get('value')
        
        # 2. Preparar datos para la petición POST
        post_data = {
            'q': video_url,
            'url': video_url,       # algunos sitios usan 'url'
            'v': video_id           # otros usan 'v'
        }
        if csrf_token:
            post_data['_token'] = csrf_token

        # Endpoint típico (puede ser '/process', '/convert', '/download', etc.)
        # Probamos varias rutas comunes
        possible_endpoints = [
            '/process',
            '/convert',
            '/download',
            '/api/convert',
            '/'
        ]
        
        response = None
        used_endpoint = None
        
        for endpoint in possible_endpoints:
            try:
                resp = session.post(
                    f'https://labpsych.pl{endpoint}',
                    data=post_data,
                    headers={
                        'X-Requested-With': 'XMLHttpRequest',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    timeout=20
                )
                if resp.status_code == 200:
                    response = resp
                    used_endpoint = endpoint
                    break
            except:
                continue
        
        if response is None:
            return {"status": False, "error": "No se pudo contactar al servidor de conversión"}

        # 3. Parsear respuesta
        result_data = parse_response(response.text, video_id)
        
        if not result_data.get('formats'):
            # Si no se encontraron enlaces, intentar una segunda petición con delay
            time.sleep(2)
            # Algunos sitios usan polling con un ID de tarea
            task_id_match = re.search(r'data-task-id=["\']([^"\']+)["\']', response.text)
            if task_id_match:
                task_id = task_id_match.group(1)
                poll_response = session.get(
                    f'https://labpsych.pl/status/{task_id}',
                    headers={'X-Requested-With': 'XMLHttpRequest'},
                    timeout=10
                )
                if poll_response.status_code == 200:
                    result_data = parse_response(poll_response.text, video_id)
        
        # Filtrar por formato si se especificó
        if format_preference and result_data.get('formats'):
            result_data['formats'] = [
                f for f in result_data['formats']
                if f['type'].lower() == format_preference.lower()
            ]
        
        result_data['status'] = bool(result_data.get('formats'))
        result_data['video_id'] = video_id
        
        if not result_data['status']:
            result_data['error'] = 'No se encontraron enlaces de descarga'
        
        return result_data

    except requests.exceptions.RequestException as e:
        return {"status": False, "error": f"Error de conexión: {str(e)}"}
    except Exception as e:
        return {"status": False, "error": f"Error procesando datos: {str(e)}"}


def extract_youtube_id(url):
    """Extrae el ID del video de YouTube de diversos formatos de URL."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[?&]|$)',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'embed\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def parse_response(html_content, video_id):
    """Extrae enlaces de descarga del HTML de respuesta."""
    soup = BeautifulSoup(html_content, 'html.parser')
    formats = []
    title = ''
    
    # Intentar obtener título del video
    title_elem = soup.find('h2') or soup.find('h3') or soup.find('div', class_='video-title')
    if title_elem:
        title = title_elem.text.strip()
    else:
        # Extraer del atributo data-title o similar
        title_div = soup.find('div', {'data-title': True})
        if title_div:
            title = title_div['data-title']
        else:
            title = f"YouTube Video {video_id}"
    
    # Método 1: Enlaces directos en etiquetas <a> con atributos específicos
    for link in soup.find_all('a', href=True):
        href = link['href']
        if any(ext in href.lower() for ext in ['.mp3', '.mp4', 'download', 'getvideo']):
            # Determinar tipo
            if '.mp3' in href.lower() or 'mp3' in link.text.lower():
                ftype = 'mp3'
                quality = extract_quality(link.text, 'mp3')
            else:
                ftype = 'mp4'
                quality = extract_quality(link.text, 'mp4')
            
            # Hacer URL absoluta
            if href.startswith('/'):
                href = f'https://labpsych.pl{href}'
            elif not href.startswith('http'):
                href = f'https://labpsych.pl/{href}'
            
            formats.append({
                'type': ftype,
                'quality': quality,
                'url': href,
                'size': extract_size(link.text)
            })
    
    # Método 2: Buscar en data-attributes de botones
    if not formats:
        for btn in soup.find_all(['button', 'a'], {'data-url': True}):
            data_url = btn.get('data-url')
            if data_url:
                ftype = 'mp3' if 'mp3' in btn.get('data-type', '').lower() else 'mp4'
                formats.append({
                    'type': ftype,
                    'quality': btn.get('data-quality', 'unknown'),
                    'url': data_url if data_url.startswith('http') else f'https://labpsych.pl{data_url}',
                    'size': btn.get('data-size', '')
                })
    
    # Método 3: Buscar en script JSON incrustado
    if not formats:
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string:
                # Buscar patrones de URL de descarga
                matches = re.findall(r'"(https?://[^"]+\.(mp3|mp4)[^"]*)"', script.string, re.I)
                for match in matches:
                    url = match[0].replace('\\/', '/')
                    ftype = match[1].lower()
                    formats.append({
                        'type': ftype,
                        'quality': 'unknown',
                        'url': url,
                        'size': ''
                    })
                # Buscar objetos JSON con links
                try:
                    json_data = re.search(r'(\[.*?\]|\{.*?\})', script.string, re.DOTALL)
                    if json_data:
                        data = json.loads(json_data.group())
                        if isinstance(data, dict):
                            links = data.get('links') or data.get('formats') or data.get('downloads')
                            if links:
                                for item in links:
                                    formats.append({
                                        'type': item.get('type', 'mp4'),
                                        'quality': item.get('quality', 'unknown'),
                                        'url': item.get('url') or item.get('link'),
                                        'size': item.get('size', '')
                                    })
                except:
                    pass
    
    return {
        'title': title,
        'formats': formats
    }


def extract_quality(text, file_type):
    """Intenta extraer la calidad (ej. 320kbps, 1080p) del texto."""
    if file_type == 'mp3':
        match = re.search(r'(\d{2,3})\s*kbps', text, re.I)
        return f"{match.group(1)}kbps" if match else 'standard'
    else:
        match = re.search(r'(\d{3,4})p', text, re.I)
        return f"{match.group(1)}p" if match else 'standard'


def extract_size(text):
    """Extrae tamaño de archivo (ej. 5.2 MB)."""
    match = re.search(r'(\d+(\.\d+)?)\s*(MB|KB|GB)', text, re.I)
    return match.group(0) if match else ''


# ============================================================
# ENDPOINT DE API
# ============================================================

def run(ctx):
    """
    Función principal para el endpoint.
    Espera parámetros en query string:
        - url (obligatorio): URL del video de YouTube
        - format (opcional): 'mp3' o 'mp4'
    """
    req = ctx['req']
    query_params = req.get('query', {})
    
    video_url = query_params.get('url') or query_params.get('q') or query_params.get('v')
    if not video_url:
        return {
            'status': False,
            'error': 'Parámetro requerido',
            'message': "Debes proporcionar 'url' con el enlace de YouTube",
            'code': 400
        }
    
    format_pref = query_params.get('format', '').lower()
    
    start_time = time.time()
    data = scrape_labpsych(video_url, format_pref)
    data['tiempo_respuesta'] = f"{time.time() - start_time:.2f}s"
    
    # Si se pide descarga directa (opcional), podríamos devolver el archivo
    # pero por ahora solo enlaces.
    
    return data


# ============================================================
# CONFIGURACIÓN DEL ENDPOINT
# ============================================================

endpoints = [
    {
        'metode': 'GET',
        'endpoint': '/download/ytmp3and4',
        'name': 'YouTube to MP3/MP4 Downloader',
        'category': 'Downloader',
        'description': 'Obtiene enlaces de descarga MP3 y MP4 de videos de YouTube usando labpsych.pl',
        'tags': ['YouTube', 'MP3', 'MP4', 'Downloader', 'Converter'],
        'example': '?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&format=mp3',
        'parameters': [
            {
                'name': 'url',
                'in': 'query',
                'required': True,
                'schema': {'type': 'string'},
                'description': 'URL del video de YouTube',
                'example': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            },
            {
                'name': 'format',
                'in': 'query',
                'required': False,
                'schema': {'type': 'string', 'enum': ['mp3', 'mp4']},
                'description': 'Filtrar por formato de salida',
                'example': 'mp3',
            }
        ],
        'isPremium': False,
        'isMaintenance': False,
        'isPublic': True,
        'middleware': ['apiKey'],
        'run': run
    }
]
