import io, os, requests, random
from PIL import Image, ImageDraw, ImageFont, ImageOps
import streamlit as st
from dotenv import load_dotenv

# -------- Config & env
load_dotenv()
AI_API_URL = os.getenv("AI_IMAGE_API_URL", "").strip()
AI_API_KEY = os.getenv("AI_IMAGE_API_KEY", "").strip()

st.set_page_config(page_title="AI Banner Maker (Logo + Pipe)", page_icon="🎨", layout="centered")
st.title("🎉 AI Banner Maker for Festivals (Logo + Pipe Fixed)")
st.caption("Enter a prompt for the background, upload your logo & product image, and export a banner.")

# -------- Helpers
def get_resampler():
    try:
        # Pillow >= 10
        return Image.Resampling.LANCZOS
    except Exception:
        # Back-compat
        return Image.LANCZOS

RESAMPLE = get_resampler()

def hex_to_rgba(color_str: str, alpha: int = 255):
    if isinstance(color_str, str) and color_str.startswith("#") and len(color_str) == 7:
        return tuple(int(color_str[i:i+2], 16) for i in (1, 3, 5)) + (alpha,)
    return (255, 255, 255, alpha)

def place_image(base_rgba, overlay_img, target_width_px, anchor="Top-Right", margin=20):
    """Scale overlay by width and paste onto base using alpha composition."""
    if overlay_img.mode != "RGBA":
        overlay_img = overlay_img.convert("RGBA")
    w_ratio = target_width_px / max(1, overlay_img.width)
    new_size = (max(1, int(overlay_img.width * w_ratio)), max(1, int(overlay_img.height * w_ratio)))
    o = overlay_img.resize(new_size, RESAMPLE)
    bx, by = base_rgba.size
    x, y = margin, margin

    # vertical centers
    if "Center" in anchor:
        y = (by - o.height)//2
    if anchor == "Left-Center":
        x = margin
    if anchor == "Right-Center":
        x = bx - o.width - margin

    # corners & bottom-center
    if anchor == "Top-Left":
        x, y = margin, margin
    elif anchor == "Top-Right":
        x, y = bx - o.width - margin, margin
    elif anchor == "Bottom-Left":
        x, y = margin, by - o.height - margin
    elif anchor == "Bottom-Right":
        x, y = bx - o.width - margin, by - o.height - margin
    elif anchor == "Bottom-Center":
        x, y = (bx - o.width)//2, by - o.height - margin

    base_rgba.alpha_composite(o, dest=(x, y))
    return base_rgba

def draw_text_multiline(img_rgba, text, y_frac, fill, font_size_ratio=0.07, shadow_on=True, font_path=None):
    """Draw centered, wrapped text using textbbox (Pillow 10+ safe)."""
    if not text:
        return

    W, H = img_rgba.size
    # Choose font
    try:
        fnt = ImageFont.truetype(font_path or "DejaVuSans.ttf", max(12, int(W * font_size_ratio)))
    except Exception:
        fnt = ImageFont.load_default()

    draw = ImageDraw.Draw(img_rgba)

    def measure(t: str):
        # textbbox returns (l, t, r, b)
        l, t0, r, b = draw.textbbox((0, 0), t, font=fnt)
        return (r - l), (b - t0)

    # Simple word wrap
    max_w = int(W * 0.9)
    words = text.split()
    lines, line = [], ""
    for word in words:
        trial = (line + " " + word).strip()
        ww, _ = measure(trial)
        if not line or ww <= max_w:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)

    # Compute total block height
    line_heights = []
    total_h = 0
    for l in lines:
        _, lh = measure(l)
        line_heights.append(lh)
        total_h += lh
    total_h += (len(lines) - 1) * 6

    y = int(H * y_frac - total_h / 2)
    fill_rgba = hex_to_rgba(fill, 255) if isinstance(fill, str) else (255, 255, 255, 255)

    for i, l in enumerate(lines):
        tw, th = measure(l)
        x = (W - tw) // 2
        if shadow_on:
            draw.text((x + 2, y + 2), l, font=fnt, fill=(0, 0, 0, 160))
        draw.text((x, y), l, font=fnt, fill=fill_rgba)
        y += line_heights[i] + 6

def gradient_fallback(width, height):
    """Nice-looking vertical gradient for when AI isn't configured/available."""
    top = tuple(random.randint(10, 80) for _ in range(3)) + (255,)
    bottom = tuple(random.randint(120, 200) for _ in range(3)) + (255,)
    base = Image.new("RGBA", (width, height), top)
    overlay = Image.new("RGBA", (width, height), bottom)
    # simple gradient mask
    mask = Image.linear_gradient("L").resize((1, height))
    mask = ImageOps.expand(mask, border=(0,0,0,0)).resize((width, height), RESAMPLE)
    base = Image.composite(overlay, base, mask)
    return base

def call_ai_background(prompt, width, height):
    """Replace with your provider; returns RGBA image. Falls back to gradient."""
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

# -------- UI: sizes
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
    W = st.sidebar.number_input("Width", value=1080, step=10, min_value=400)
    H = st.sidebar.number_input("Height", value=1080, step=10, min_value=400)
else:
    W, H = size_map[size_label]

# -------- Inputs & styling
prompt = st.text_area("Background prompt", "Warm golden festive lights, soft bokeh, elegant clean backdrop")
headline = st.text_input("Headline", "Happy Diwali from XYZ Pipes!")
subtext = st.text_input("Subtext (optional)", "Special Festive Offers on Quality Pipes")
brand_color = st.color_picker("Headline/Subtext color", "#FFFFFF")
shadow = st.checkbox("Add text shadow (better contrast)", value=True)

logo_file = st.file_uploader("Upload logo (PNG with transparency preferred)", type=["png", "jpg", "jpeg"])
pipe_file = st.file_uploader("Upload product image (pipe photo)", type=["png", "jpg", "jpeg"])

st.subheader("Placement & Scale")
col1, col2 = st.columns(2)
with col1:
    logo_scale = st.slider("Logo width (% of canvas)", 5, 40, 18)
    logo_pos = st.selectbox("Logo position", ["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right"])
with col2:
    pipe_scale = st.slider("Pipe width (% of canvas)", 15, 70, 45)
    pipe_pos = st.selectbox("Pipe position", ["Left-Center", "Right-Center", "Bottom-Center"])

# Optional custom font path
font_path = st.text_input("Custom TTF font path (optional)", "")

# -------- Generate
if st.button("Generate Banner", type="primary"):
    base = call_ai_background(prompt.strip(), int(W), int(H)).convert("RGBA")

    # Place product and logo
    if pipe_file:
        pipe_img = Image.open(pipe_file)
        base = place_image(base, pipe_img, int(W * pipe_scale / 100), anchor=pipe_pos)
    if logo_file:
        logo_img = Image.open(logo_file)
        base = place_image(base, logo_img, int(W * logo_scale / 100), anchor=logo_pos)

    # Text layers
    draw_text_multiline(base, headline.strip(), y_frac=0.18, fill=brand_color, font_size_ratio=0.075,
                        shadow_on=shadow, font_path=font_path or None)
    draw_text_multiline(base, subtext.strip(),  y_frac=0.30, fill=brand_color, font_size_ratio=0.045,
                        shadow_on=shadow, font_path=font_path or None)

    st.image(base, caption="Preview", use_column_width=True)

    buf = io.BytesIO()
    base.convert("RGB").save(buf, format="PNG")
    st.download_button("Download PNG", data=buf.getvalue(), file_name="banner.png", mime="image/png")

st.caption("Tip: Save your preferred sizes/positions as a template. For AI, set AI_IMAGE_API_URL & AI_IMAGE_API_KEY in your environment.")
