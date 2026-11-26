from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_author, get_visible_library_block, get_owned_library_block
from app.models import User, LibraryBlock
from app.schemas.library import LibraryCreate, LibraryMetadata, LibraryCreated, LibraryDetails, LibraryItem, LibraryTag
from app.services import library
from app.services.form_validation import InvalidFormError

router = APIRouter(prefix="/library", tags=["Библиотека блоков"])


@router.get("/blocks", response_model=list[LibraryItem])
def list_blocks(query: str | None = None, tag: str | None = None,
                scope: Literal["mine", "public", "all"] = "all", is_test: bool | None = None,
                limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0),
                user: User = Depends(require_author), db: Session = Depends(get_db)):
    return library.list_items(db, user.id, query=query, tag=tag, scope=scope, is_test=is_test, limit=limit, offset=offset)


@router.get("/blocks/{id}", response_model=LibraryDetails, response_model_exclude_unset=True)
def get_block(item: LibraryBlock = Depends(get_visible_library_block), db: Session = Depends(get_db)):
    return library.get_details(db, item)


@router.post("/blocks", status_code=201, response_model=LibraryCreated)
def create_block(data: LibraryCreate, user: User = Depends(require_author), db: Session = Depends(get_db)):
    try:
        return library.create_library_block(db, user.id, data)
    except InvalidFormError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.put("/blocks/{id}", response_model=LibraryItem)
def update_block(data: LibraryMetadata, item: LibraryBlock = Depends(get_owned_library_block), db: Session = Depends(get_db)):
    return library.update_library_block(db, item, data)


@router.delete("/blocks/{id}", status_code=204)
def delete_block(item: LibraryBlock = Depends(get_owned_library_block), db: Session = Depends(get_db)):
    library.delete_library_block(db, item)
    return Response(status_code=204)


@router.get("/tags", response_model=list[LibraryTag])
def list_tags(query: str | None = None, user: User = Depends(require_author), db: Session = Depends(get_db)):
    return library.list_tags(db, user.id, query)
