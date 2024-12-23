from datetime import datetime, timezone
from bson import ObjectId
from fastapi import Request, HTTPException, status
from config.config import session_collection
from utils.auth import api

async def validate_session(request: Request, return_data: bool):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                            headers={'Location': '/'})

    session = session_collection.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={'Location': '/'})

    token = session.get("token")
    user = await api.get_user(token)

    if datetime.now(timezone.utc).replace(tzinfo=None) > session.get("token_expires_at") or user.get("code") == 0:
        if not await api.reload(session_id, session.get("refresh_token")):
            raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                                headers={'Location': '/logout'})
        else:
            return await validate_session(request, return_data=return_data)

    if "id" not in user:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                            headers={'Location': '/logout'})
    if return_data:
        return {'user': user, 'session': session}

async def validate_session_without_data(request: Request):
    return await validate_session(request, return_data=False)

async def validate_session_with_data(request: Request):
    return await validate_session(request, return_data=True)