from datetime import date
from pathlib import Path
import random
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1080
BG = (16, 18, 22)
FG = (235, 238, 245)
MUTED = (155, 160, 172)

MODE = "FOUR"  # "ONE" or "FOUR"


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


def center_text(draw: ImageDraw.ImageDraw, text: str, font, y: int, fill):
    b = draw.textbbox((0, 0), text, font=font)
    x = (W - (b[2] - b[0])) // 2
    draw.text((x, y), text, font=font, fill=fill)


def daily_rng(d: date) -> random.Random:
    return random.Random(d.year * 10000 + d.month * 100 + d.day)


def load_faces(folder="faces"):
    p = Path(folder)
    if not p.exists():
        return []
    faces = []
    for fp in sorted(p.glob("*.png")):
        try:
            faces.append(Image.open(fp).convert("RGBA"))
        except Exception:
            pass
    return faces


def crop_to_content(img: Image.Image) -> Image.Image:
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def circle_mask(size: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((0, 0, size - 1, size - 1), fill=255)
    return m


def place_face(canvas_rgba: Image.Image, face_rgba: Image.Image, center_xy, radius_px, tilt_deg):
    face = crop_to_content(face_rgba)
    target = max(2, int(radius_px * 2.25))
    face = face.resize((target, target), Image.Resampling.LANCZOS)
    if tilt_deg:
        face = face.rotate(tilt_deg, resample=Image.Resampling.BICUBIC, expand=True)
    side = max(face.size)
    tmp = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    tmp.alpha_composite(face, ((side - face.width) // 2, (side - face.height) // 2))
    m = circle_mask(side)
    tmp.putalpha(ImageChops.multiply(tmp.split()[-1], m))
    x, y = center_xy
    canvas_rgba.alpha_composite(tmp, (x - side // 2, y - side // 2))


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


def make_base(today: date, doy: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    font_title = load_font(64)
    font_big = load_font(220)
    font_date = load_font(54)
    font_small = load_font(46)

    center_text(draw, "Täna on aasta", font_title, 140, FG)
    center_text(draw, f"{doy}. päev", font_big, 320, FG)
    center_text(draw, today.strftime("%d.%m.%Y"), font_date, 610, MUTED)
    center_text(draw, f"Tee {doy} kätekõverdust", font_small, 760, FG)

    return img


def render_one(base_rgb: Image.Image, faces, rng: random.Random, t: float, today: date) -> Image.Image:
    img = base_rgb.convert("RGBA")
    draw = ImageDraw.Draw(img)

    cx, cy, s = 540, 900, 1.05
    (hx, hy), hr = draw_stickman(draw, cx, cy, s, t, FG)

    if faces:
        face = rng.choice(faces)
        tilt = rng.randint(-10, 10)
        face = crop_to_content(face)
        target = max(2, int(hr * 2.25))
        face = face.resize((target, target), Image.Resampling.LANCZOS)
        if tilt:
            face = face.rotate(tilt, resample=Image.Resampling.BICUBIC, expand=True)
        side = max(face.size)
        tmp = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        tmp.alpha_composite(face, ((side - face.width) // 2, (side - face.height) // 2))
        m = circle_mask(side)
        tmp.putalpha(ImageChops.multiply(tmp.split()[-1], m))
        img.alpha_composite(tmp, (hx - side // 2, hy - side // 2))

    return img


def render_four(base_rgb: Image.Image, faces, rng: random.Random, frame_i: int, frames_n: int, today: date) -> Image.Image:
    img = base_rgb.convert("RGBA")
    draw = ImageDraw.Draw(img)

    centers = [(220, 905), (460, 905), (700, 905), (940, 905)]
    scales = [0.70, 0.78, 0.72, 0.82]
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

    base_phase = frame_i / (frames_n - 1) if frames_n > 1 else 1.0

    for i, (cx, cy) in enumerate(centers):
        t = (base_phase * speeds[i]) % 1.0
        (hx, hy), hr = draw_stickman(draw, cx, cy, scales[i], t, FG)

        face = chosen[i]
        if face is not None:
            face2 = crop_to_content(face)
            target = max(2, int(hr * 2.30))
            face2 = face2.resize((target, target), Image.Resampling.LANCZOS)
            if tilts[i]:
                face2 = face2.rotate(tilts[i], resample=Image.Resampling.BICUBIC, expand=True)
            side = max(face2.size)
            tmp = Image.new("RGBA", (side, side), (0, 0, 0, 0))
            tmp.alpha_composite(face2, ((side - face2.width) // 2, (side - face2.height) // 2))
            m = circle_mask(side)
            tmp.putalpha(ImageChops.multiply(tmp.split()[-1], m))
            img.alpha_composite(tmp, (hx - side // 2, hy - side // 2))

    return img


def to_palette(im_rgba: Image.Image) -> Image.Image:
    return im_rgba.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)


def main():
    today = date.today()
    doy = day_of_year(today)

    out_dir = Path("public")
    out_dir.mkdir(exist_ok=True)

    faces = load_faces("faces")
    rng = daily_rng(today)

    base = make_base(today, doy)

    base.save(out_dir / "day.png", format="PNG", optimize=True)

    fps = 12
    duration_s = 2.0
    frames_n = max(12, int(fps * duration_s))
    frame_ms = int(1000 / fps)

    frames = []
    for i in range(frames_n):
        if MODE == "ONE":
            t = i / (frames_n - 1) if frames_n > 1 else 1.0
            fr = render_one(base, faces, rng, t, today)
        else:
            fr = render_four(base, faces, rng, i, frames_n, today)
        frames.append(to_palette(fr))

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
    from PIL import ImageChops
    main()
