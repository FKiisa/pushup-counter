from datetime import date
from pathlib import Path
import random
from PIL import Image, ImageDraw, ImageFont, ImageChops

W, H = 1920, 600
BG = (16, 18, 22)
FG = (235, 238, 245)
MUTED = (155, 160, 172)

MODE = "FOUR"
FACE_SCALE = 3.2


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


def crop_to_content(img: Image.Image) -> Image.Image:
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def circle_mask(size: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((0, 0, size - 1, size - 1), fill=255)
    return m


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


def ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)


def pushup_phase(t: float) -> float:
    t = t % 1.0
    if t <= 0.5:
        return ease_in_out(t / 0.5)
    return ease_in_out((1.0 - t) / 0.5)


def draw_stickman(draw: ImageDraw.ImageDraw, cx: int, cy: int, s: float, t: float, color):
    p = pushup_phase(t)
    dy = int((28 * s) * p)
    w = max(2, int(6 * s))

    gy = cy + int(70 * s)
    draw.line((cx - int(120 * s), gy, cx + int(120 * s), gy), fill=color, width=max(2, int(4 * s)))

    head_r = int(14 * s)
    hx = cx - int(55 * s)
    hy = cy - int(15 * s) + dy
    draw.ellipse((hx - head_r, hy - head_r, hx + head_r, hy + head_r), outline=color, width=w)

    shx = cx - int(35 * s)
    shy = cy + int(5 * s) + dy
    hipx = cx + int(10 * s)
    hipy = cy + int(20 * s) + dy
    draw.line((shx, shy, hipx, hipy), fill=color, width=w)

    hand_y = gy - int(5 * s)
    hand_x1 = cx - int(10 * s)
    hand_x2 = cx + int(10 * s)

    elbow_drop = int((5 * s) + (17 * s) * p)
    elx1, ely1 = cx - int(25 * s), cy + int(25 * s) + dy + elbow_drop
    elx2, ely2 = cx - int(5 * s), cy + int(25 * s) + dy + elbow_drop

    draw.line((shx, shy, elx1, ely1), fill=color, width=w)
    draw.line((elx1, ely1, hand_x1, hand_y), fill=color, width=w)
    draw.line((shx, shy, elx2, ely2), fill=color, width=w)
    draw.line((elx2, ely2, hand_x2, hand_y), fill=color, width=w)

    foot_y = gy - int(5 * s)
    foot_x = cx + int(85 * s)
    knee_drop = int((10 * s) * p)
    kx, ky = cx + int(40 * s), cy + int(38 * s) + dy + knee_drop
    draw.line((hipx, hipy, kx, ky), fill=color, width=w)
    draw.line((kx, ky, foot_x, foot_y), fill=color, width=w)

    return (hx, hy), head_r


def face_stamp(face_rgba: Image.Image, target_px: int, tilt_deg: int):
    f = crop_to_content(face_rgba)
    f = f.resize((target_px, target_px), Image.Resampling.LANCZOS)
    if tilt_deg:
        f = f.rotate(tilt_deg, resample=Image.Resampling.BICUBIC, expand=True)
    side = max(f.size)
    tmp = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    tmp.alpha_composite(f, ((side - f.width) // 2, (side - f.height) // 2))
    m = circle_mask(side)
    tmp.putalpha(ImageChops.multiply(tmp.split()[-1], m))
    return tmp


def make_base(today: date, doy: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    font_big = load_font(92)
    font_mid = load_font(56)

    draw.text((80, 70), f"Tee {doy} kätekõverdust", font=font_big, fill=FG)
    draw.text((80, 170), f"{today.strftime('%d.%m.%Y')}  •  Aasta {doy}. päev", font=font_mid, fill=MUTED)

    return img


def render_four(base_rgb: Image.Image, frame_i: int, frames_n: int, faces, speeds, tilts, stamps):
    img = base_rgb.convert("RGBA")
    draw = ImageDraw.Draw(img)

    centers = [(240, 360), (720, 360), (1200, 360), (1680, 360)]
    scales = [0.88, 0.90, 0.86, 0.92]

    base_phase = frame_i / (frames_n - 1) if frames_n > 1 else 1.0

    for i, (cx, cy) in enumerate(centers):
        t = (base_phase * speeds[i]) % 1.0
        (hx, hy), hr = draw_stickman(draw, cx, cy, scales[i], t, FG)

        if stamps[i] is not None:
            st = stamps[i]
            img.alpha_composite(st, (hx - st.width // 2, hy - st.height // 2))

    return img


def render_one(base_rgb: Image.Image, t: float, stamp):
    img = base_rgb.convert("RGBA")
    draw = ImageDraw.Draw(img)

    cx, cy, s = 960, 380, 1.1
    (hx, hy), hr = draw_stickman(draw, cx, cy, s, t, FG)

    if stamp is not None:
        img.alpha_composite(stamp, (hx - stamp.width // 2, hy - stamp.height // 2))

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

    fps = 12
    duration_s = 2.0
    frames_n = max(12, int(fps * duration_s))
    frame_ms = int(1000 / fps)

    if MODE == "ONE":
        stamp = None
        if faces:
            f = rng.choice(faces)
            tilt = rng.randint(-10, 10)
            stamp = face_stamp(f, int(14 * 1.1 * FACE_SCALE * 2), tilt)
        frames = []
        for i in range(frames_n):
            t = i / (frames_n - 1) if frames_n > 1 else 1.0
            frames.append(to_palette(render_one(base, t, stamp)))
    else:
        speeds = [rng.uniform(0.75, 1.65) for _ in range(4)]
        tilts = [rng.randint(-12, 12) for _ in range(4)]
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
                stamps.append(face_stamp(chosen[i], int(14 * 0.9 * FACE_SCALE * 2), tilts[i]))

        frames = []
        for i in range(frames_n):
            frames.append(to_palette(render_four(base, i, frames_n, faces, speeds, tilts, stamps)))

    frames[0].save(
        out_dir / reminding.gif if False else out_dir / "day.gif",
        save_all=True,
        append_images=frames[1:],
        duration=frame_ms,
        loop=0,
        optimize=False,
        disposal=2,
    )


if __name__ == "__main__":
    main()
