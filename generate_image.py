from datetime import date
from pathlib import Path
import random
from PIL import Image, ImageDraw, ImageFont, ImageChops

W, H = 1080, 1920
BG = (16, 18, 22)
FG = (235, 238, 245)
MUTED = (155, 160, 172)

FACE_SCALE = 2.25
FPS = 12
DURATION_S = 2.0


def day_of_year(d: date) -> int:
    return (d - date(d.year, 1, 1)).days + 1


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def daily_rng(d: date) -> random.Random:
    return random.Random(d.year * 10000 + d.month * 100 + d.day)


def load_faces(folder="faces"):
    p = Path(folder)
    if not p.exists():
        return []
    out = []
    for fp in sorted(p.glob("*.png")):
        try:
            out.append(Image.open(fp).convert("RGBA"))
        except Exception:
            pass
    return out


def crop_to_content(img: Image.Image) -> Image.Image:
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def circle_mask(size: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((0, 0, size - 1, size - 1), fill=255)
    return m


def ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)


def pushup_phase(t: float) -> float:
    t = t % 1.0
    if t <= 0.5:
        return ease_in_out(t / 0.5)
    return ease_in_out((1.0 - t) / 0.5)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def face_stamp(face_rgba: Image.Image, size_px: int, tilt_deg: int):
    f = crop_to_content(face_rgba.convert("RGBA"))
    f = f.resize((size_px, size_px), Image.Resampling.LANCZOS)
    if tilt_deg:
        f = f.rotate(tilt_deg, resample=Image.Resampling.BICUBIC, expand=True)
    side = max(f.size)
    tmp = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    tmp.alpha_composite(f, ((side - f.width) // 2, (side - f.height) // 2))
    m = circle_mask(side)
    tmp.putalpha(ImageChops.multiply(tmp.split()[-1], m))
    return tmp


def draw_front_pushup(draw: ImageDraw.ImageDraw, cx: int, cy: int, s: float, t: float, color):
    p = pushup_phase(t)
    body_drop = int((46 * s) * p)

    w = max(2, int(8 * s))
    gy = cy + int(120 * s)
    draw.line((cx - int(170 * s), gy, cx + int(170 * s), gy), fill=color, width=max(2, int(5 * s)))

    head_r = int(30 * s)
    hx, hy = cx, cy - int(45 * s) + body_drop
    draw.ellipse((hx - head_r, hy - head_r, hx + head_r, hy + head_r), outline=color, width=w)

    shoulder_y = cy + int(10 * s) + body_drop
    hip_y = cy + int(62 * s) + body_drop
    shoulder_w = int(90 * s)
    hip_w = int(130 * s)

    draw.line((cx - shoulder_w, shoulder_y, cx + shoulder_w, shoulder_y), fill=color, width=w)
    draw.line((cx - hip_w, hip_y, cx + hip_w, hip_y), fill=color, width=w)
    draw.line((cx, shoulder_y, cx, hip_y), fill=color, width=w)

    hand_y = gy - int(10 * s)
    hand_x = int(110 * s)

    elbow_y = int(lerp(shoulder_y + int(22 * s), shoulder_y + int(92 * s), p))
    draw.line((cx - shoulder_w, shoulder_y, cx - shoulder_w, elbow_y), fill=color, width=w)
    draw.line((cx + shoulder_w, shoulder_y, cx + shoulder_w, elbow_y), fill=color, width=w)

    draw.line((cx - shoulder_w, elbow_y, cx - hand_x, hand_y), fill=color, width=w)
    draw.line((cx + shoulder_w, elbow_y, cx + hand_x, hand_y), fill=color, width=w)

    foot_y = gy - int(10 * s)
    foot_x = int(150 * s)
    knee_y = int(lerp(hip_y + int(12 * s), hip_y + int(42 * s), p))

    draw.line((cx - hip_w, hip_y, cx - int(78 * s), knee_y), fill=color, width=w)
    draw.line((cx + hip_w, hip_y, cx + int(78 * s), knee_y), fill=color, width=w)
    draw.line((cx - int(78 * s), knee_y, cx - foot_x, foot_y), fill=color, width=w)
    draw.line((cx + int(78 * s), knee_y, cx + foot_x, foot_y), fill=color, width=w)

    return (hx, hy), head_r


def make_base(today: date, doy: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    font_title = load_font(86)
    font_mid = load_font(52)

    draw.text((70, 90), f"Tee {doy} kätekõverdust", font=font_title, fill=FG)
    draw.text((70, 200), f"{today.strftime('%d.%m.%Y')}  •  Aasta {doy}. päev", font=font_mid, fill=MUTED)

    return img


def render_four(base_rgb: Image.Image, frame_i: int, frames_n: int, speeds, stamps, tilts):
    img = base_rgb.convert("RGBA")
    draw = ImageDraw.Draw(img)

    centers = [(540, 520), (540, 860), (540, 1200), (540, 1540)]
    scales = [1.0, 1.0, 1.0, 1.0]

    base_phase = frame_i / (frames_n - 1) if frames_n > 1 else 1.0

    for i, (cx, cy) in enumerate(centers):
        t = (base_phase * speeds[i]) % 1.0
        (hx, hy), hr = draw_front_pushup(draw, cx, cy, scales[i], t, FG)
        st = stamps[i]
        if st is not None:
            img.alpha_composite(st, (hx - st.width // 2, hy - st.height // 2))

    return img


def to_palette(im_rgba: Image.Image) -> Image.Image:
    return im_rgba.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)


def main():
    today = date.today()
    doy = day_of_year(today)

    out_dir = Path("public")
    out_dir.mkdir(exist_ok=True)

    rng = daily_rng(today)
    faces = load_faces("faces")

    base = make_base(today, doy)
    base.save(out_dir / "day.png", format="PNG", optimize=True)

    frames_n = max(12, int(FPS * DURATION_S))
    frame_ms = int(1000 / FPS)

    speeds = [rng.uniform(0.75, 1.65) for _ in range(4)]
    tilts = [rng.randint(-10, 10) for _ in range(4)]

    chosen = []
    if faces:
        pool = faces[:]
        rng.shuffle(pool)
        while len(pool) < 4:
            pool += faces
        chosen = pool[:4]
    else:
        chosen = [None, None, None, None]

    stamps = []
    for i in range(4):
        if chosen[i] is None:
            stamps.append(None)
        else:
            stamps.append(face_stamp(chosen[i], int(30 * 1.0 * FACE_SCALE * 2), tilts[i]))

    frames = []
    for i in range(frames_n):
        frames.append(to_palette(render_four(base, i, frames_n, speeds, stamps, tilts)))

    frames[0].save(
        out_dir / "day.gif",
        save_all=True,
        append_images=frames[1:],
        duration=frame_ms,
        loop=0,
        optimize=False,
        disposal=2,
    )


if __name__ == "__main__":
    main()
