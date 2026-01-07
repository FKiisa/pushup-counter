from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def day_of_year(d: date) -> int:
    return (d - date(d.year, 1, 1)).days + 1


def is_leap(y: int) -> bool:
    return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def center_text(draw: ImageDraw.ImageDraw, text: str, font, y: int, img_w: int, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    x = (img_w - w) // 2
    draw.text((x, y), text, font=font, fill=fill)


def main():
    today = date.today()
    doy = day_of_year(today)
    total = 366 if is_leap(today.year) else 365

    W, H = 1080, 1080
    bg = (16, 18, 22)
    fg = (235, 238, 245)
    muted = (155, 160, 172)

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    font_title = load_font(64)
    center_text(draw, "Täna on aasta", font_title, y=140, img_w=W, fill=fg)

    font_big = load_font(220)
    center_text(draw, f"{doy}. päev", font_big, y=320, img_w=W, fill=fg)

    font_date = load_font(54)
    center_text(draw, today.strftime("%d.%m.%Y"), font_date, y=610, img_w=W, fill=muted)

    font_small = load_font(46)
    center_text(draw, f"Tee {doy} kätekõverdust", font_small, y=760, img_w=W, fill=fg)

    bar_w = 760
    bar_h = 16
    bar_x = (W - bar_w) // 2
    bar_y = 880
    radius = 8


    draw.rounded_rectangle(
        (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h),
        radius=radius,
        fill=(40, 44, 54),
    )

    frac = doy / total
    fill_w = max(1, int(bar_w * frac))
    draw.rounded_rectangle(
        (bar_x, bar_y, bar_x + fill_w, bar_y + bar_h),
        radius=radius,
        fill=(235, 238, 245),
    )

    out_dir = Path("public")
    out_dir.mkdir(exist_ok=True)

    img.save(out_dir / "day.png", format="PNG", optimize=True)
    print(f"Generated: public/day.png (DAY {doy}/{total})")


if __name__ == "__main__":
    main()
