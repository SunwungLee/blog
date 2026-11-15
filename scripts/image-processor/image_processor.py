"""Image resizing. Pillow is only needed for pixel work and is imported lazily."""

from pathlib import Path

from common.errors import SkillError

ALLOWED_FORMATS = {"jpg", "jpeg", "png", "webp"}


def plan_resize(width, height, max_width=1200):
    """Deterministic target size that keeps aspect ratio and never upscales."""
    if width <= 0 or height <= 0 or max_width <= 0:
        raise ValueError("dimensions must be positive")
    if width <= max_width:
        return width, height
    return max_width, max(1, round(height * max_width / width))


_PIL_FORMATS = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}


def resize_image(src, dst, max_width=1200, quality=85):
    """Resize without upscaling and save without EXIF/GPS metadata (privacy)."""
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise SkillError("UNKNOWN_FAILURE", "Pillow가 설치되지 않았습니다(requirements.txt 참고).") from exc
    ext = Path(str(dst)).suffix.lower().lstrip(".")
    if ext not in ALLOWED_FORMATS:
        raise SkillError("INVALID_INPUT", "지원하지 않는 이미지 형식입니다.")
    with Image.open(src) as opened:
        img = ImageOps.exif_transpose(opened)  # bake orientation in before EXIF is dropped
        new_size = plan_resize(img.width, img.height, max_width)
        if new_size != img.size:
            img = img.resize(new_size, Image.LANCZOS)
        if ext in ("jpg", "jpeg") and img.mode != "RGB":
            img = img.convert("RGB")
        # Copy pixels only, so no EXIF/GPS/XMP metadata from the source is carried over.
        clean = Image.new(img.mode, img.size)
        clean.paste(img)
        if img.mode == "P" and img.getpalette():
            clean.putpalette(img.getpalette())
        clean.save(dst, format=_PIL_FORMATS[ext], quality=quality, optimize=True)
    return {"path": str(dst), "width": new_size[0], "height": new_size[1]}
