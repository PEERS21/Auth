import functools
from typing import Optional
from aiohttp import web
import hmac
import hashlib
from common.db_init import AsyncSessionLocal
from common.db_models import IssuedToken
from sqlalchemy import select, delete
import time
from os import getenv

async def find_token_hash(token_hash: str) -> Optional[dict]:
    now = int(time.time())
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(IssuedToken).where(IssuedToken.token_hash == token_hash))
        row = q.scalars().first()
        if not row:
            return None
        if row.expires_at < now:
            await session.execute(delete(IssuedToken).where(IssuedToken.token_hash == token_hash))
            await session.commit()
            return None
        return {"user": row.user_login, "issued_at": row.issued_at, "expires_at": row.expires_at}


def make_hmac(token: str) -> str:
    return hmac.new(getenv("SECRET_KEY", "").encode('utf-8'), token.encode('utf-8'), hashlib.sha256).hexdigest()

def extract_token_from_request(request: web.Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return request.cookies.get(getenv("COOKIE_NAME", ""))