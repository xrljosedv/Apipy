import requests
import uuid
import base64
import time
from flask import request, Response
import json

def generate_magic_image(prompt):
    def generate_client_id():
        import secrets
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')

    form_data = {
        'prompt': prompt,
        'output_format': 'bytes',
        'user_profile_id': 'null',
        'anonymous_user_id': str(uuid.uuid4()),
        'request_timestamp': f"{time.time():.3f}",
        'user_is_subscribed': 'false',
        'client_id': generate_client_id()
    }

    headers = {
        'accept': 'application/json, text/plain, */*',
        'origin': 'https://magicstudio.com',
        'referer': 'https://magicstudio.com/ai-art-generator/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        resp = requests.post(
            'https://ai-api.magicstudio.com/api/ai-art-generator',
            data=form_data,
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        raise Exception(f"MagicStudio API error: {str(e)}")

def run(ctx):
    req = ctx['req']
    res = ctx['res']
    prompt = req.get('query', {}).get('prompt', '')

    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        return {
            'status': False,
            'error': 'Missing required parameter',
            'message': "The 'prompt' parameter is required",
            'code': 400
        }

    prompt = prompt.strip()
    if len(prompt) > 1000:
        return {
            'status': False,
            'error': 'Prompt too long',
            'message': 'Prompt must be 1000 characters or less',
            'code': 400
        }

    try:
        image_bytes = generate_magic_image(prompt)
        filename = f"magicstudio_{int(time.time())}.jpg"

        from flask import current_app
        if current_app:
            return Response(
                image_bytes,
                mimetype='image/jpeg',
                headers={
                    'Content-Disposition': f'inline; filename="{filename}"',
                    'Cache-Control': 'public, max-age=3600'
                }
            )
        else:
            return {
                'status': True,
                'data': {
                    'image': base64.b64encode(image_bytes).decode(),
                    'format': 'jpeg',
                    'size': len(image_bytes),
                    'filename': filename
                },
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
    except Exception as e:
        return {
            'status': False,
            'error': 'Image generation failed',
            'message': str(e),
            'code': 500
        }

endpoints = [
    {
        'metode': 'GET',
        'endpoint': '/ai/magicstudio',
        'name': 'MagicStudio AI Image Generator',
        'category': 'AI Image',
        'description': 'Genera arte AI a partir de un prompt de texto.',
        'tags': ['AI', 'Image Generation', 'Art'],
        'example': '?prompt=portrait of a wizard with a long beard',
        'parameters': [
            {
                'name': 'prompt',
                'in': 'query',
                'required': True,
                'schema': {
                    'type': 'string',
                    'minLength': 1,
                    'maxLength': 1000,
                },
                'description': 'El prompt para generar la imagen',
                'example': 'portrait of a wizard with a long beard',
            }
        ],
        'isPremium': False,
        'isMaintenance': False,
        'isPublic': True,
        'middleware': ['apiKey'],
        'run': run
    }
]