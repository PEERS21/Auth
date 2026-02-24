import os
from os import getenv
import secrets
import time
import aiohttp_jinja2
import jinja2
from aiohttp import web
from sqlalchemy import delete, select
import views
from auth import extract_token_from_request, make_hmac, find_token_hash
from common.db_init import AsyncSessionLocal, ENGINE
from common.db_models import IssuedToken, Base, Blacklist
from redis_client import init_redis, close_redis
from state_manager import store_state, pop_state
import aiohttp_cors
import re

async def init_db():
    async with ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_engine(app):
    await ENGINE.dispose()


async def store_issued_token(user_login: str,
                             token_hash: str,
                             ttl_days: int = int(getenv("SERVER_TOKEN_DAYS"))):
    now = int(time.time())
    exp = now + ttl_days * 24 * 3600
    async with AsyncSessionLocal() as session:
        it = IssuedToken(user_login=user_login,
                         token_hash=token_hash,
                         issued_at=now,
                         expires_at=exp)
        session.add(it)
        await session.commit()


async def is_blacklisted(login: str) -> bool:
    async with AsyncSessionLocal() as session:
        stmt = select(Blacklist).where(Blacklist.login == login)
        res = await session.execute(stmt)
        row = res.scalars().one_or_none()
        return row is not None


async def add_to_blacklist(login: str, reason: str | None = None):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            exists_stmt = select(Blacklist).where(Blacklist.login == login)
            r = await session.execute(exists_stmt)
            if r.scalars().one_or_none():
                return
            bl = Blacklist(login=login, reason=reason)
            session.add(bl)
            await session.commit()


async def del_to_blacklist(login: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                delete(Blacklist).where(Blacklist.login == login))
            await session.commit()


def _unauthorized(message="Unauthorized"):
    raise web.HTTPUnauthorized(text=message)


def _extract_bearer(request: web.Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth:
        _unauthorized("Missing Authorization header")
    parts = auth.split()
    return parts[1]


async def authorize_request(request: web.Request):
    token = _extract_bearer(request)
    if token != getenv("AUTH_STATIC_TOKEN"):
        _unauthorized("Invalid token")


routes = web.RouteTableDef()
ORIGIN_RE = re.compile(r"^https://([a-z0-9-]+\.)?tamelaos\.fun$")


@web.middleware
async def security_headers_middleware(request, handler):
    resp = await handler(request)
    if isinstance(resp, web.Response):
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault('Content-Security-Policy', (
            "default-src 'self' https://fonts.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https://doc-08-2c-docs.googleusercontent.com; "
            "media-src 'self' blob: data:; "
            "connect-src 'self' https://rentaldisk.tamelaos.fun"))

    origin = request.headers.get("Origin")
    # preflight
    if request.method == "OPTIONS":
        resp = web.Response(status=204)
        if origin and ORIGIN_RE.match(origin):
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = request.headers.get(
                "Access-Control-Request-Headers", "Authorization,Content-Type"
            )
        return resp

    if origin and ORIGIN_RE.match(origin):
        # echo origin — важно для credentials (cookies)
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        # опционально
        resp.headers.setdefault("Access-Control-Expose-Headers", "Content-Length")
    return resp

@routes.post('/send_code')
async def send_code(request: web.Request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {'error': 'Что-то пошло не так, обновите страницу'}, status=400)
    state = data.get('state')
    login = data.get('login')
    if not state:
        return web.json_response({'error': 'Обновите страницу'}, status=400)
    if not login:
        return web.json_response({'error': 'Вы забыли вписать логин'},
                                 status=400)
    next_url = await pop_state(request.app['redis'], state)
    if next_url is None:
        return web.json_response(
            {
                'error':
                'Вы уже отправили код, если это не так или не пришёл обновите страницу'
            },
            status=400)

    try:
        if await is_blacklisted(login):
            audio_url = "/static/blocked.mp3"
            return web.json_response(
                {
                    'ok': False,
                    'blacklisted': True,
                    'audio_url': audio_url,
                    'error': 'Вас никто не услышал...'
                },
                status=200)
    except Exception as e:
        return web.json_response({'error': 'Ошибка проверки черного списка'},
                                 status=500)

    code = str(secrets.randbelow(1000000)).zfill(6)

    try:
        """
        TODO
        GMAIL SEND
        """
        print(f" ✅ Письмо отправлено: TODO")
    except RuntimeError as e:
        print(f" ❌ Ошибка отправки: {e}")
        return web.json_response(
            {'error': 'Не удалось отправить код. Попробуйте позже.'},
            status=500)
    except Exception as e:
        print(f" ❌ Неожиданная ошибка: {e}")
        return web.json_response({'error': 'Внутренняя ошибка сервера'},
                                 status=500)

    await store_state(request.app['redis'], make_hmac(code), next_url)
    return web.json_response({
        'ok': True,
        'state': f'{make_hmac(code)}'
    }, status=200)


@routes.post('/verif_code')
async def verif_code(request: web.Request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {'error': 'Что-то пошло не так, обновите страницу'}, status=400)
    state = data.get('state')
    login = data.get('login')
    password = data.get('code')
    if not state:
        return web.json_response(
            {'error': 'Для начала давайте вышлем Вам код'}, status=400)
    next_url = await pop_state(request.app['redis'], state)
    if next_url is None:
        return web.json_response(
            {
                'error':
                'Вы уже отправили код, если это не так обновите страницу'
            },
            status=400)
    if not login:
        return web.json_response({'error': 'Вы забыли вписать логин'},
                                 status=400)
    if not password:
        return web.json_response({'error': 'Вы забыли вписать код'},
                                 status=400)

    raw_token = secrets.token_urlsafe(48)
    token_hash = make_hmac(raw_token)
    await store_issued_token(login, token_hash)
    resp = web.json_response({'ok': True, 'next': next_url})
    max_age = int(getenv("SERVER_TOKEN_DAYS", 0)) * 24 * 3600
    resp.set_cookie(getenv("COOKIE_NAME"),
                    raw_token,
                    max_age=max_age,
                    httponly=True,
                    secure=True,
                    samesite='Lax',
                    domain='.tamelaos.fun',
                    path='/')
    return resp


@routes.get('/verify')
async def verify(request: web.Request):
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Bearer '):
        token = auth.split(' ', 1)[1]
    else:
        token = request.cookies.get(getenv("COOKIE_NAME"))
    if not token:
        raise web.HTTPFound(location=getenv("LOGIN_URL"))
    token_hash = make_hmac(token)
    info = await find_token_hash(token_hash)
    if not info:
        raise web.HTTPFound(location=getenv("LOGIN_URL"))
    """
    return web.json_response({
        'ok': True,
        'user': "tamelaos_test"
    })"""


@routes.post('/revoke')
async def revoke(request: web.Request):
    try:
        await authorize_request(request)
    except web.HTTPUnauthorized:
        raise
    try:
        data = await request.json()
        login = data.get('login')
    except Exception as e:
        return web.json_response({'error': 'bad_request'}, status=400)
    if not login:
        return web.json_response({'error': 'missing_token'}, status=400)
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(IssuedToken).where(IssuedToken.user_login == login))
        await session.commit()
    return web.json_response({'ok': True})


@routes.post('/ban')
async def ban(request: web.Request):
    try:
        await authorize_request(request)
    except web.HTTPUnauthorized:
        raise
    try:
        data = await request.json()
        login = data.get('login')
    except Exception:
        return web.json_response({'error': 'bad_request'}, status=400)
    if not login:
        return web.json_response({'error': 'missing_login'}, status=400)
    await add_to_blacklist(login, "banned")
    return web.json_response({'ok': True})


@routes.post('/pardon')
async def unban(request: web.Request):
    try:
        await authorize_request(request)
    except web.HTTPUnauthorized:
        raise
    try:
        data = await request.json()
        login = data.get('login')
    except Exception:
        return web.json_response({'error': 'bad_request'}, status=400)
    if not login:
        return web.json_response({'error': 'missing_login'}, status=400)
    await del_to_blacklist(login)
    return web.json_response({'ok': True})


async def on_startup(app):
    await init_redis(app)
    await init_db()


async def on_cleanup(app):
    await close_engine(app)
    await close_redis(app)


def make_app():
    app = web.Application()
    app.router.add_static('/static/', path='static', name='static')
    app.add_routes(routes)
    app.router.add_get('/login', views.index)
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("templates"))

    app.middlewares.append(security_headers_middleware)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app


if __name__ == "__main__":
    main_frame = make_app()
    web.run_app(main_frame,
                host="0.0.0.0",
                port=int(getenv("PORT", 0)))
