from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/method", tags=["tag"])
async def post_mothod(request: Request):
    return {"method":"my method!"}