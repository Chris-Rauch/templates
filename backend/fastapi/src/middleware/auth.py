import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from fastapi import HTTPException, Request, Response
from starlette.responses import JSONResponse
import httpx

AUTH_SERVICE_URL = "http://localhost:8001/auth/auth_request"
IGNORE_ENDPOINTS = {
    "/health",
    "/docs",
    "/login",
    "/register",
    "/openapi.json",
}

class AuthResponse(BaseModel):
    user_uuid: uuid.UUID
    permissions: list[str]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        endpoint = request.url.path.strip("/").split("/")[-1]

        if endpoint in IGNORE_ENDPOINTS:
            return await call_next(request)

        auth = request.headers.get("authorization")
        if not auth:
            return JSONResponse({"detail": "Missing Authorization header"}, status_code=401)

        service = request.scope.get("root_path", "").strip("/") or request.url.path.strip("/").split("/")[0]

        auth_response = await auth_user(auth=auth, service=service)

        if isinstance(auth_response, JSONResponse):
            return auth_response

        setattr(request.state, 'identity', auth_response)
        return await call_next(request)


async def auth_user(auth: str, service: str) -> AuthResponse | JSONResponse:
    """
    Sends an http request to AuthService, requesting the validity of the provided auth string. If
    valid, AuthService returns the requester's uuid in the response.
    
    :param auth: Auth String. Should be 'Bearer <jwt-token>'
    :type auth: string
    :param service: The service being requested. Options are robotalker and/or positive_pay
    :type service: str
    :return: user_uuid if valid. JSON Response otherwise
    :rtype: str | Any
    """
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.get(
                AUTH_SERVICE_URL,
                headers={'authorization': auth},
                params={"service": service}
            )

            if auth_response.status_code == 200:
                data = auth_response.json()
                user_uuid = data["user_uuid"]
                permissions = data["permissions"]
                return AuthResponse(
                    user_uuid=user_uuid,
                    permissions=permissions
                )
            else:
                return JSONResponse(
                    content={"detail": auth_response.text},
                    status_code=auth_response.status_code
                )
        except httpx.RequestError:
            return JSONResponse(
                content={"detail": "Auth service unavailable"},
                status_code=503
            )
        except Exception as e:
            return JSONResponse(content={"detail": str(e)}, status_code=501)

def get_identity(request: Request) -> uuid.UUID:
    """
    Used with the AuthMiddleware injection. This function does not authenticate, rather it grabs the
    data set by the middleware. This can be used as a dependency injection along with the middleware
    authentication to retrieve the requesting user's uuid 
    
    :param request: FastAPI request object.
    :type request: Request
    """   
    user_uuid = request.state.identity.user_uuid
    if not user_uuid:
        raise HTTPException(status_code=500, detail="Missing identity in request")
    return user_uuid

def get_permissions(request: Request) -> list[str]:
    """
    Used with the AuthMiddleware injection. This function does not authenticate, rather it grabs the
    data set by the middleware. This can be used as a dependency injection along with the middleware
    authentication to retrieve the requesting user's uuid 
    
    :param request: FastAPI request object.
    :type request: Request
    """   
    permissions = request.state.identity.permissions
    if permissions is None:
        raise HTTPException(status_code=500, detail="Missing permissions in request")
    return permissions
