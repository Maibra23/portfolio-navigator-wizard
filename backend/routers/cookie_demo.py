from fastapi import APIRouter, Response

router = APIRouter(prefix="/api", tags=["cookie-demo"])

@router.get("/set-cookie")
def set_cookie(response: Response):
    response.set_cookie(
        key="session_id",
        value="example-session-id",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return {"message": "Cookie set"} 