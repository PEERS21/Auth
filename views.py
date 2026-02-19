import aiohttp_jinja2
import secrets

from aiohttp import web

from auth_server import store_state
from auth import extract_token_from_request, make_hmac, find_token_hash


@aiohttp_jinja2.template("index.html")
async def index(request):
    next_url = request.query.get('next', '/')
    token = extract_token_from_request(request)
    if token:
        token_hash = make_hmac(token)
        if token_hash:
            info = await find_token_hash(token_hash)
            if info:
                raise web.HTTPFound(location=next_url)
    state = secrets.token_urlsafe(32)
    await store_state(request.app['redis'], state, next_url)
    return {'state_get': state}
