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


def days_in_year(year: int) -> int:
    jan1 = date(year, 1, 1)
    jan1_next = date(year + 1, 1, 1)
    return (jan1_next - jan1).days


def total_pushups_until_day(day_n: int) -> int:
    return day_n * (day_n + 1) // 2


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for p in (
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
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
    w = max(2, int(8 * s))
    gy = cy + int(126 * s)
    draw.line((cx - int(170 * s), gy, cx + int(170 * s), gy), fill=color, width=max(2, int(5 * s)))

    shoulder_y = int(lerp(cy - int(6 * s), cy + int(52 * s), p))
    hip_y = shoulder_y + int(lerp(54 * s, 34 * s, p))
    shoulder_w = int(92 * s)
    hip_w = int(132 * s)

    head_r = int(30 * s)
    hx = cx
    hy = shoulder_y - int(58 * s) + int(lerp(0, 8 * s, p))
    draw.ellipse((hx - head_r, hy - head_r, hx + head_r, hy + head_r), outline=color, width=w)

    left_shoulder = (cx - shoulder_w, shoulder_y)
    right_shoulder = (cx + shoulder_w, shoulder_y)
    left_hip = (cx - hip_w, hip_y)
    right_hip = (cx + hip_w, hip_y)

    draw.line((left_shoulder, right_shoulder), fill=color, width=w)
    draw.line((left_hip, right_hip), fill=color, width=w)
    draw.line(((cx, shoulder_y), (cx, hip_y)), fill=color, width=w)

    hand_y = gy - int(9 * s)
    hand_x = int(115 * s)
    left_hand = (cx - hand_x, hand_y)
    right_hand = (cx + hand_x, hand_y)

    elbow_y = int(lerp(shoulder_y + int(14 * s), shoulder_y + int(74 * s), p))
    elbow_inset = int(lerp(12 * s, 36 * s, p))
    left_elbow = (cx - shoulder_w + elbow_inset, elbow_y)
    right_elbow = (cx + shoulder_w - elbow_inset, elbow_y)

    draw.line((left_shoulder, left_elbow), fill=color, width=w)
    draw.line((left_elbow, left_hand), fill=color, width=w)
    draw.line((right_shoulder, right_elbow), fill=color, width=w)
    draw.line((right_elbow, right_hand), fill=color, width=w)

    foot_y = gy - int(9 * s)
    foot_x = int(152 * s)
    left_foot = (cx - foot_x, foot_y)
    right_foot = (cx + foot_x, foot_y)

    knee_y = int(lerp(hip_y + int(8 * s), hip_y + int(30 * s), p))
    knee_out = int(74 * s)
    left_knee = (cx - knee_out, knee_y)
    right_knee = (cx + knee_out, knee_y)

    draw.line((left_hip, left_knee), fill=color, width=w)
    draw.line((left_knee, left_foot), fill=color, width=w)
    draw.line((right_hip, right_knee), fill=color, width=w)
    draw.line((right_knee, right_foot), fill=color, width=w)

    return (hx, hy), head_r


def make_base(today: date, doy: int, total_done: int, yearly_target: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    font_title = load_font(86)
    font_mid = load_font(52)
    font_small = load_font(42)

    draw.text((70, 90), f"Tee {doy} kätekõverdust", font=font_title, fill=FG)
    draw.text((70, 200), f"{today.strftime('%d.%m.%Y')}  •  Aasta {doy}. päev", font=font_mid, fill=MUTED)

    stats_y = 1650
    draw.text((70, stats_y), f"Kokku tehtud: {total_done}", font=font_mid, fill=FG)
    draw.text((70, stats_y + 62), f"Aasta eesmärk: {yearly_target}", font=font_small, fill=MUTED)

    bar_x, bar_y = 70, stats_y + 132
    bar_w, bar_h = 940, 28
    progress = min(1.0, total_done / yearly_target) if yearly_target else 0.0
    fill_w = int(bar_w * progress)

    bar_bg = (92, 99, 114)
    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=14, fill=bar_bg)
    if fill_w > 0:
        fill_radius = min(14, max(3, fill_w // 2))
        draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), radius=fill_radius, fill=FG)

    draw.text((bar_x, bar_y + 42), f"{total_done} / {yearly_target} ({progress * 100:.1f}%)", font=font_small, fill=MUTED)

    return img


def render_four(base_rgb: Image.Image, frame_i: int, frames_n: int, cycle_counts, stamps, tilts):
    img = base_rgb.convert("RGBA")
    draw = ImageDraw.Draw(img)

    centers = [(540, 480), (540, 800), (540, 1120), (540, 1440)]
    scales = [1.0, 1.0, 1.0, 1.0]

    base_phase = frame_i / frames_n if frames_n > 0 else 0.0

    for i, (cx, cy) in enumerate(centers):
        t = (base_phase * cycle_counts[i]) % 1.0
        (hx, hy), hr = draw_front_pushup(draw, cx, cy, scales[i], t, FG)
        st = stamps[i]
        if st is not None:
            img.alpha_composite(st, (hx - st.width // 2, hy - st.height // 2))

    return img


def main():
    today = date.today()
    doy = day_of_year(today)
    year_days = days_in_year(today.year)
    total_done = total_pushups_until_day(doy)
    yearly_target = total_pushups_until_day(year_days)

    out_dir = Path("public")
    out_dir.mkdir(exist_ok=True)

    rng = daily_rng(today)
    faces = load_faces("faces")

    base = make_base(today, doy, total_done, yearly_target)
    base.save(out_dir / "day.png", format="PNG", optimize=True)

    frames_n = max(12, int(FPS * DURATION_S))
    frame_ms = int(1000 / FPS)

    cycle_counts = [rng.randint(1, 3) for _ in range(4)]
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

    raw_frames = []
    for i in range(frames_n):
        raw_frames.append(render_four(base, i, frames_n, cycle_counts, stamps, tilts).convert("RGB"))

    first_palette = raw_frames[0].convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
    frames = [first_palette]
    for frm in raw_frames[1:]:
        frames.append(frm.quantize(palette=first_palette, dither=Image.Dither.NONE))

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
