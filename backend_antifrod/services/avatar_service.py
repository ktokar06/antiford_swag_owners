"""Account-owned avatars stored as normalized JPEGs in PostgreSQL."""
import base64
import warnings
from io import BytesIO

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.dialects.postgresql import insert

from core.models.user import UserAvatar

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000


def normalize_image(data: bytes) -> bytes:
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Фото должно быть не больше 5 МБ")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(415, "Выберите JPEG, PNG или WebP")
                if source.width * source.height > MAX_PIXELS:
                    raise HTTPException(413, "Изображение должно содержать не больше 20 млн пикселей")
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGBA")
                image.thumbnail((512, 512), Image.Resampling.LANCZOS)
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                output = BytesIO()
                background.save(output, format="JPEG", quality=85)
                return output.getvalue()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(413, "Слишком большое разрешение изображения") from None
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(415, "Не удалось прочитать фото. Выберите JPEG, PNG или WebP") from None


def avatar_url(db, user_id: int) -> str | None:
    avatar = db.get(UserAvatar, user_id)
    return "data:image/jpeg;base64," + base64.b64encode(avatar.image).decode("ascii") if avatar else None


def save_avatar(db, user_id: int, data: bytes) -> None:
    image = normalize_image(data)
    stmt = insert(UserAvatar).values(user_id=user_id, image=image)
    db.execute(stmt.on_conflict_do_update(index_elements=[UserAvatar.user_id], set_={"image": image}))
    db.commit()
