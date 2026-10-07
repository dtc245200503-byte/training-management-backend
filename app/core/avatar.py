import base64
import io
import warnings

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_AVATAR_BYTES = 2 * 1024 * 1024
MAX_AVATAR_PIXELS = 20_000_000
AVATAR_MIME_TYPES = {"image/jpeg", "image/png"}
AVATAR_FORMATS = {"JPEG", "PNG"}
AVATAR_SIZE = 256
AVATAR_THUMBNAIL_SIZE = 64


def encode_avatar(image: Image.Image) -> str:
    output = io.BytesIO()
    # Re-encode without original bytes/metadata and keep each MySQL TEXT bounded.
    for quality in (85, 70, 50):
        output.seek(0)
        output.truncate()
        image.save(output, format="JPEG", quality=quality, optimize=True)
        if output.tell() <= 45_000:
            break
    return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def prepare_avatar(content: bytes, content_type: str | None) -> tuple[str, str]:
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="Ảnh đại diện không được vượt quá 2 MB.")
    if content_type not in AVATAR_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Vui lòng chọn ảnh JPG hoặc PNG.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in AVATAR_FORMATS:
                    raise HTTPException(status_code=400, detail="Vui lòng chọn ảnh JPG hoặc PNG.")
                if image.width * image.height > MAX_AVATAR_PIXELS:
                    raise HTTPException(status_code=400, detail="Ảnh quá lớn. Vui lòng chọn ảnh tối đa 20 triệu điểm ảnh.")
                image.load()
                image = ImageOps.exif_transpose(image)
                image = ImageOps.fit(image, (AVATAR_SIZE, AVATAR_SIZE), method=Image.Resampling.LANCZOS)
                rgba = image.convert("RGBA")
                flattened = Image.new("RGB", rgba.size, "white")
                flattened.paste(rgba, mask=rgba.getchannel("A"))
                thumbnail = flattened.resize((AVATAR_THUMBNAIL_SIZE, AVATAR_THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
                return encode_avatar(flattened), encode_avatar(thumbnail)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=400, detail="Tệp ảnh không hợp lệ hoặc bị hỏng. Vui lòng chọn ảnh khác.")
