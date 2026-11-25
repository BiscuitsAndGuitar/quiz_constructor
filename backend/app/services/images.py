from uuid import uuid4

from app.models import Image

MAX_IMAGE_SIZE = 5 * 1024 * 1024


def image_type(data: bytes):
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif", "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


def save_image(db, owner_id, data, kind, directory):
    extension, content_type = kind
    directory.mkdir(parents=True, exist_ok=True)
    file_name = f"{uuid4().hex}.{extension}"
    path = directory / file_name
    try:
        path.write_bytes(data)
        image = Image(owner_id=owner_id, file_name=file_name, content_type=content_type, size=len(data))
        db.add(image)
        db.flush()
        result = {"id": image.id, "url": f"/uploads/{file_name}"}
        db.commit()
        return result
    except Exception:
        db.rollback()
        # При ошибке записи в БД не оставляем файл от неудачной загрузки.
        path.unlink(missing_ok=True)
        raise
