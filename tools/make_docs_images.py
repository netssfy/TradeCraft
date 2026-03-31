from pathlib import Path
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "docs" / "images"
RAW_DIR = IMAGES_DIR / "raw"

OUTPUT_MAP = {
    "trader-list.png": "ui-trader-list.png",
    "trader-create.png": "ui-trader-create.png",
    "trader-detail.png": "ui-trader-detail.png",
    "strategy-code.png": "ui-strategy-code.png",
    "market-data.png": "ui-market-data.png",
}


def trim_white_border(img: Image.Image, threshold: int = 245) -> Image.Image:
    rgb = img.convert("RGB")
    px = rgb.load()
    w, h = rgb.size

    def row_is_white(y: int) -> bool:
        for x in range(w):
            r, g, b = px[x, y]
            if not (r >= threshold and g >= threshold and b >= threshold):
                return False
        return True

    def col_is_white(x: int) -> bool:
        for y in range(h):
            r, g, b = px[x, y]
            if not (r >= threshold and g >= threshold and b >= threshold):
                return False
        return True

    top = 0
    while top < h and row_is_white(top):
        top += 1

    bottom = h - 1
    while bottom >= 0 and row_is_white(bottom):
        bottom -= 1

    left = 0
    while left < w and col_is_white(left):
        left += 1

    right = w - 1
    while right >= 0 and col_is_white(right):
        right -= 1

    if left >= right or top >= bottom:
        return rgb

    return rgb.crop((left, top, right + 1, bottom + 1))


def main() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    processed = []
    for raw_name, out_name in OUTPUT_MAP.items():
        src = RAW_DIR / raw_name
        if not src.exists():
            raise FileNotFoundError(f"Missing raw screenshot: {src}")

        img = Image.open(src)
        cropped = trim_white_border(img)
        cropped.save(IMAGES_DIR / out_name, optimize=True)
        processed.append(cropped)

    base_w, base_h = processed[0].size
    gif_frames = [
        frame.resize((base_w, base_h), Image.Resampling.LANCZOS) for frame in processed
    ]

    gif_frames[0].save(
        IMAGES_DIR / "ui-overview.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=1400,
        loop=0,
        optimize=True,
    )

    print("Generated screenshots and GIF in docs/images")


if __name__ == "__main__":
    main()
