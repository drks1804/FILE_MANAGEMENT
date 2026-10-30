from fastapi import APIRouter, Depends,status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import User
from app.service.security import get_current_user
from app.handlers.search_handler import semantic_search_handler

router=APIRouter(
    prefix="/search",
    tags=["Search files"]
)

@router.get("/query", status_code=status.HTTP_200_OK)
def semantic_search(
    query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return semantic_search_handler(
        query,
        current_user.user_id,
        db
    )