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


def text_w(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


def center_x(draw: ImageDraw.ImageDraw, text: str, font, W: int) -> int:
    return (W - text_w(draw, text, font)) // 2


def rounded_bar(draw, x, y, w, h, r, fill):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=r, fill=fill)


def make_frame(today: date, doy: int, total: int, t: float) -> Image.Image:
    W, H = 1080, 1080
    bg = (16, 18, 22)
    fg = (235, 238, 245)
    muted = (155, 160, 172)
    bar_bg = (40, 44, 54)

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    font_title = load_font(64)
    font_big = load_font(220)
    font_date = load_font(54)
    font_small = load_font(46)

    e = 1 - (1 - t) ** 3

    fade = 0.80 + 0.20 * e

    def scale_color(c):
        return tuple(max(0, min(255, int(v * fade))) for v in c)

    fg_f = scale_color(fg)
    muted_f = scale_color(muted)

    title = "Täna on aasta"
    big = f"{doy}. päev"
    dstr = today.strftime("%d.%m.%Y")
    bottom = f"Tee {doy} kätekõverdust"

    draw.text((center_x(draw, title, font_title, W), 140), title, font=font_title, fill=fg_f)
    draw.text((center_x(draw, big, font_big, W), 320), big, font=font_big, fill=fg_f)
    draw.text((center_x(draw, dstr, font_date, W), 610), dstr, font=font_date, fill=muted_f)
    draw.text((center_x(draw, bottom, font_small, W), 760), bottom, font=font_small, fill=fg_f)

    bar_w = 760
    bar_h = 16
    bar_x = (W - bar_w) // 2
    bar_y = 880
    r = 8

    rounded_bar(draw, bar_x, bar_y, bar_w, bar_h, r, bar_bg)
    frac = doy / total
    target_w = max(1, int(bar_w * frac))
    fill_w = max(1, int(target_w * e))
    rounded_bar(draw, bar_x, bar_y, fill_w, bar_h, r, fg)

    return img


def main():
    today = date.today()
    doy = day_of_year(today)
    total = 366 if is_leap(today.year) else 365

    out_dir = Path("public")
    out_dir.mkdir(exist_ok=True)

    png = make_frame(today, doy, total, t=1.0)
    png.save(out_dir / "day.png", format="PNG", optimize=True)

    fps = 12
    duration_s = 2.4
    frames_n = int(duration_s * fps)

    frames = []
    for i in range(frames_n):
        t = i / (frames_n - 1) if frames_n > 1 else 1.0
        frames.append(make_frame(today, doy, total, t=t).convert("P", palette=Image.Palette.ADAPTIVE))

    frame_ms = int(1000 / fps)

    frames[0].save(
        out_dir / "day.gif",
        save_all=True,
        append_images=frames[1:],
        duration=frame_ms,
        loop=0,
        optimize=True,
        disposal=2,
    )

    print(f"Generated: public/day.png and public/day.gif (DAY {doy}/{total})")


if __name__ == "__main__":
    main()
