from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import require_author
from app.models import User
from app.services.images import MAX_IMAGE_SIZE, image_type, save_image

router = APIRouter(tags=["Картинки"])


@router.post("/images", status_code=201)
async def upload_image(file: UploadFile, user: User = Depends(require_author), db: Session = Depends(get_db)):
    try:
        # Один лишний байт позволяет отличить точный предел от превышения.
        data = await file.read(MAX_IMAGE_SIZE + 1)
        if len(data) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=413, detail="Картинка должна быть не больше 5 МБ")
        kind = image_type(data)
        if kind is None:
            raise HTTPException(status_code=422, detail="Допустимы только картинки JPEG, PNG, GIF и WebP")
        return save_image(db, user.id, data, kind, settings.UPLOADS_DIR)
    finally:
        await file.close()
