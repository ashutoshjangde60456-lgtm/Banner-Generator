import io, os, random, glob, math, requests
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat

# ---- Optional translation (English -> Hindi)
try:
    from googletrans import Translator
    translator = Translator()
except Exception:
    translator = None

# ============ Config ============
load_dotenv()
AI_API_URL = os.getenv("AI_IMAGE_API_URL", "").strip()
AI_API_KEY = os.getenv("AI_IMAGE_API_KEY", "").strip()

ASSETS_DIR = Path("assets")
PIPES_DIR = ASSETS_DIR / "pipes"
FEST_DIR  = ASSETS_DIR / "festivals"

FESTIVAL_PRESETS = {
    "Diwali":   "Warm golden festive lights, soft bokeh, deep maroon + gold accents, elegant clean backdrop",
    "Holi":     "Color splash background with powdery gradients, vibrant pink yellow blue, clean and bright",
    "Christmas":"Cozy warm lights bokeh, soft red & green accents, subtle snow sparkle, premium feel",
    "Eid":      "Royal night sky gradient, moon & star motifs, warm lantern glow, elegant geometric pattern",
    "New Year": "Fireworks bokeh, confetti gradient, glossy premium look, dark-to-light vignette"
}

# ============ UI ============
st.set_page_config(page_title="AI Festival Banner Maker", page_icon="✨", layout="centered")
st.title("✨ Festival Banner Maker (Auto pipe + Logo + AI background)")

with st.expander("How this works", expanded=False):
    st.write(
        "- Upload only your **logo** and type a prompt (or pick a festival preset).\n"
        "- The app can **auto-pick a suitable pipe photo** from `assets/pipes/` or you can upload one.\n"
        "- Choose a **festival** to add relevant decorative elements from `assets/festivals/`.\n"
        "- Type headline in English, tick **Hindi** to auto-translate (needs an Internet connection for googletrans)."
    )

# ---- Size selection
size_label = st.sidebar.selectbox(
    "Choose banner size",
    ["Instagram Post (1080x1080)", "Instagram Story (1080x1920)", "Facebook Post (1200x630)", "Custom"]
)
size_map = {
    "Instagram Post (1080x1080)": (1080, 1080),
    "Instagram Story (1080x1920)": (1080, 1920),
    "Facebook Post (1200x630)": (1200, 630),
}
if size_label == "Custom":
    W = st.sidebar.number_input("Width", value=1080, step=10, min_value=600)
    H = st.sidebar.number_input("Height", value=1080, step=10, min_value=600)
else:
    W, H = size_map[size_label]

# ---- Festival + background
festival = st.selectbox("Festival", list(FESTIVAL_PRESETS.keys()))
use_preset = st.checkbox("Use festival background preset", value=True)
prompt = st.text_area(
    "Background prompt (used if you don't want preset, or to refine it)",
    FESTIVAL_PRESETS[festival] if use_preset else "Elegant premium background"
)

# ---- Headline & language
headline_en = st.text_input("Headline (type in English)", "Happy Diwali from XYZ Pipes!")
use_hindi = st.checkbox("Show headline in Hindi (auto-translate)")

subtext_en = st.text_input("Subtext (optional, English)", "Special Festive Offers on Quality Pipes")
use_hindi_sub = st.checkbox("Show subtext in Hindi (auto-translate)")

brand_color = st.color_picker("Headline/Subtext color", "#FFFFFF")
shadow = st.checkbox("Add text shadow", value=True)

# ---- Assets
logo_file = st.file_uploader("Upload company logo (PNG with transparency preferred)", type=["png","jpg","jpeg"])
pipe_file = st.file_uploader("(Optional) Upload pipe photo (PNG/JPG). Leave empty to auto-pick from assets/pipes/", type=["png","jpg","jpeg"])

# Placement
st.subheader("Placement & Scale")
col1, col2 = st.columns(2)
with col1:
    logo_scale = st.slider("Logo width (% of canvas)", 5, 40, 18)
    logo_pos = st.selectbox("Logo position", ["Top-Left","Top-Right","Bottom-Left","Bottom-Right"])
with col2:
    pipe_scale = st.slider("Pipe width (% of canvas)", 15, 70, 45)
    pipe_pos = st.selectbox("Pipe position", ["Left-Center","Right-Center","Bottom-Center"])

font_path_main = st.text_input("Custom Latin font (optional .ttf)", "")
font_path_hindi = st.text_input("Custom Devanagari font for Hindi (recommended)", "")

# ============ Helpers ============
def get_resampler():
    try:
        return Image.Resampling.LANCZOS
    except Exception:
        return Image.LANCZOS

RESAMPLE = get_resampler()

def load_image(file_or_path):
    if file_or_path is None:
        return None
    if hasattr(file_or_path, "read"):
        return Image.open(file_or_path).convert("RGBA")
    return Image.open(file_or_path).convert("RGBA")

def gradient_fallback(width, height):
    top = (20, 20, 28, 255)
    bottom = (120, 60, 20, 255)
    base = Image.new("RGBA", (width, height), top)
    overlay = Image.new("RGBA", (width, height), bottom)
    mask = Image.linear_gradient("L").resize((width, height))
    return Image.composite(overlay, base, mask)

def call_ai_background(prompt, width, height):
    if not AI_API_URL or not prompt.strip():
        return gradient_fallback(width, height)
    headers = {}
    if AI_API_KEY:
        headers["Authorization"] = f"Bearer {AI_API_KEY}"
    payload = {"prompt": prompt, "width": width, "height": height}
    try:
        r = requests.post(AI_API_URL, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except Exception:
        return gradient_fallback(width, height)

def text_to_hindi(txt: str) -> str:
    if not txt or not use_hindi or translator is None:
        return txt
    try:
        return translator.translate(txt, src="en", dest="hi").text
    except Exception:
        return txt

def text_to_hindi_sub(txt: str) -> str:
    if not txt or not use_hindi_sub or translator is None:
        return txt
    try:
        return translator.translate(txt, src="en", dest="hi").text
    except Exception:
        return txt

def font_from_path(path_hint: str, px: int, devanagari=False):
    # Try user-provided font first; else pick a likely system font
    try_paths = []
    if path_hint.strip():
        try_paths.append(path_hint.strip())
    if devanagari:
        try_paths += [
            "NotoSansDevanagari-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
            "/System/Library/Fonts/Supplemental/NotoSansDevanagari-Regular.ttf",
        ]
    else:
        try_paths += ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in try_paths:
        try:
            return ImageFont.truetype(p, px)
        except Exception:
            continue
    return ImageFont.load_default()

def hex_to_rgba(hex_str, a=255):
    if isinstance(hex_str, str) and hex_str.startswith("#") and len(hex_str) == 7:
        return tuple(int(hex_str[i:i+2], 16) for i in (1,3,5)) + (a,)
    return (255,255,255,a)

def draw_text_multiline(img, text, y_frac, fill, font_size_ratio=0.07, shadow_on=True, devanagari=False):
    if not text: return
    W, H = img.size
    fnt = font_from_path(font_path_hindi if devanagari else font_path_main, max(12,int(W*font_size_ratio)), devanagari=devanagari)
    draw = ImageDraw.Draw(img)

    def measure(t: str):
        l,t0,r,b = draw.textbbox((0,0), t, font=fnt)
        return (r-l, b-t0)

    # Basic wrap
    max_w = int(W*0.9)
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        ww,_ = measure(trial)
        if not line or ww <= max_w:
            line = trial
        else:
            lines.append(line); line = word
    if line: lines.append(line)

    heights = []
    total_h = 0
    for l in lines:
        _,h = measure(l); heights.append(h); total_h += h
    total_h += (len(lines)-1)*6

    y = int(H*y_frac - total_h/2)
    color = hex_to_rgba(fill, 255)
    for i, l in enumerate(lines):
        tw, th = measure(l)
        x = (W - tw)//2
        if shadow_on:
            draw.text((x+2, y+2), l, font=fnt, fill=(0,0,0,160))
        draw.text((x, y), l, font=fnt, fill=color)
        y += heights[i] + 6

def place_image(base, overlay, target_w, anchor="Right-Center", margin=24):
    if overlay.mode != "RGBA": overlay = overlay.convert("RGBA")
    scale = target_w / max(1, overlay.width)
    new_size = (max(1,int(overlay.width*scale)), max(1,int(overlay.height*scale)))
    o = overlay.resize(new_size, RESAMPLE)
    bw, bh = base.size
    x, y = margin, (bh - o.height)//2
    if anchor == "Left-Center": x = margin
    if anchor == "Right-Center": x = bw - o.width - margin
    if anchor == "Bottom-Center": x, y = (bw - o.width)//2, bh - o.height - margin
    if anchor == "Top-Left": x, y = margin, margin
    if anchor == "Top-Right": x, y = bw - o.width - margin, margin
    if anchor == "Bottom-Left": x, y = margin, bh - o.height - margin
    if anchor == "Bottom-Right": x, y = bw - o.width - margin, bh - o.height - margin
    base.alpha_composite(o, dest=(x,y))
    return base

def image_blankness_score(img):
    """Lower variance = 'blanker' background; we want more blank space."""
    gray = img.convert("L").resize((64,64))
    stat = ImageStat.Stat(gray)
    # Use inverse variance so higher is 'blanker'
    var = stat.var[0] if isinstance(stat.var, list) else stat.var
    return 1.0 / (var + 1e-6)

def choose_best_pipe_for_background(bg_img):
    """Pick a pipe from assets/pipes that will stand out reasonably."""
    candidates = sorted(glob.glob(str(PIPES_DIR / "*.*")))
    if not candidates:
        return None
    # Heuristic: prefer images with transparency if available
    rgba_first = []
    others = []
    for p in candidates:
        try:
            im = Image.open(p)
            if im.mode == "RGBA" and im.getchannel("A").getextrema()[0] < 255:
                rgba_first.append(p)
            else:
                others.append(p)
        except Exception:
            continue
    ordered = rgba_first + others
    # Very simple: just return the first 'good' one.
    return ordered[0]

def auto_side_choice(bg_img):
    """Pick Left or Right side depending on which third looks 'blanker'."""
    w,h = bg_img.size
    left_region  = bg_img.crop((0, 0, w//3, h))
    right_region = bg_img.crop((w - w//3, 0, w, h))
    left_score  = image_blankness_score(left_region)
    right_score = image_blankness_score(right_region)
    return "Left-Center" if left_score >= right_score else "Right-Center"

def add_festival_overlays(base, festival, how_many=3):
    folder = FEST_DIR / festival.lower()
    if not folder.exists():
        # also try proper-case folder names if user kept them
        folder2 = FEST_DIR / festival
        folder = folder2 if folder2.exists() else None
    if not folder:
        return base

    files = list(folder.glob("*.png"))
    if not files: 
        return base

    W,H = base.size
    k = min(how_many, len(files))
    picks = random.sample(files, k)
    for p in picks:
        try:
            elem = Image.open(p).convert("RGBA")
            # scale to 8–20% of width
            tw = int(W * random.uniform(0.08, 0.20))
            scale = tw / elem.width
            elem = elem.resize((tw, int(elem.height*scale)), RESAMPLE)
            # place in random decorative zones near corners/edges
            margin = int(min(W,H) * 0.03)
            pos_choice = random.choice([
                (margin, margin),
                (W - elem.width - margin, margin),
                (margin, H - elem.height - margin),
                (W - elem.width - margin, H - elem.height - margin),
                (W//2 - elem.width//2, margin),
                (W//2 - elem.width//2, H - elem.height - margin)
            ])
            base.alpha_composite(elem, dest=pos_choice)
        except Exception:
            continue
    return base

# ============ Generate ============
if st.button("Generate Banner", type="primary"):
    # 1) Background
    base = call_ai_background(prompt, int(W), int(H)).convert("RGBA")

    # 2) Festival overlays
    base = add_festival_overlays(base, festival, how_many=3)

    # 3) Choose/Place pipe
    if pipe_file:
        pipe_img = load_image(pipe_file)
        pipe_anchor = pipe_pos
    else:
        # auto pick from assets and auto side
        picked = choose_best_pipe_for_background(base)
        pipe_img = load_image(picked) if picked else None
        pipe_anchor = auto_side_choice(base)

    if pipe_img is not None:
        base = place_image(base, pipe_img, int(W * (pipe_scale / 100.0)), anchor=pipe_anchor)

    # 4) Place logo
    if logo_file:
        logo_img = load_image(logo_file)
        base = place_image(base, logo_img, int(W * (logo_scale / 100.0)), anchor=logo_pos)

    # 5) Text (English or Hindi)
    headline_txt = text_to_hindi(headline_en) if use_hindi else headline_en
    subtext_txt  = text_to_hindi_sub(subtext_en) if use_hindi_sub else subtext_en

    # Slightly adjust headline Y depending on aspect
    headline_y = 0.18 if H >= W else 0.22
    subtext_y  = headline_y + 0.12

    def draw_text(img, txt, y, ratio, devanagari=False):
        # Render with Pillow>=10-safe textbbox
        if not txt: return
        W_,H_ = img.size
        fnt = font_from_path(font_path_hindi if devanagari else font_path_main, max(12,int(W_*ratio)), devanagari)
        draw = ImageDraw.Draw(img)
        color = hex_to_rgba(brand_color, 255)

        def measure(t): 
            l,t0,r,b = draw.textbbox((0,0), t, font=fnt)
            return (r-l, b-t0)

        max_w = int(W_*0.9)
        words = txt.split()
        lines, line = [], ""
        for word in words:
            trial = (line+" "+word).strip()
            ww,_ = measure(trial)
            if not line or ww <= max_w:
                line = trial
            else:
                lines.append(line); line = word
        if line: lines.append(line)

        heights = []
        total_h = 0
        for l in lines:
            _,h = measure(l); heights.append(h); total_h += h
        total_h += (len(lines)-1)*6
        yy = int(H_*y - total_h/2)
        for i, l in enumerate(lines):
            tw, th = measure(l)
            x = (W_ - tw)//2
            if shadow:
                draw.text((x+2, yy+2), l, font=fnt, fill=(0,0,0,160))
            draw.text((x, yy), l, font=fnt, fill=color)
            yy += heights[i] + 6

    draw_text(base, headline_txt, headline_y, 0.075, devanagari=use_hindi)
    draw_text(base, subtext_txt,  subtext_y,  0.045, devanagari=use_hindi_sub)

    # 6) Preview + Download
    st.image(base, caption="Preview", use_column_width=True)
    buf = io.BytesIO()
    base.convert("RGB").save(buf, format="PNG")
    st.download_button("Download PNG", data=buf.getvalue(), file_name=f"{festival.lower()}_banner.png", mime="image/png")

st.caption("Tip: Put your product photos in assets/pipes/ and festival PNGs in assets/festivals/<festival>/. "
           "Set AI_IMAGE_API_URL & AI_IMAGE_API_KEY to use an AI background; otherwise you'll get a nice gradient.")
