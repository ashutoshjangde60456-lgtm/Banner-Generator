import io, os, requests
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
AI_API_URL = os.getenv("AI_IMAGE_API_URL", "https://your-ai-provider.example.com/generate")
AI_API_KEY = os.getenv("AI_IMAGE_API_KEY", "YOUR_API_KEY")

st.set_page_config(page_title="Banner Maker (AI + Brand Assets)", page_icon="🧰", layout="centered")
st.title("🎉 AI Banner Maker for Festivals (Logo + Pipe Fixed)")

# ---- Sidebar: size presets & brand options
size_label = st.sidebar.selectbox(
    "Choose banner size",
    ["Instagram Post (1080x1080)", "Instagram Story (1080x1920)", "Facebook Post (1200x630)", "Custom"]
)

size_map = {
    "Instagram Post (1080x1080)": (1080, 1080),
    "Instagram Story (1080x1920)": (1080, 1920),
    "Facebook Post (1200x630)": (1200, 630)
}

if size_label == "Custom":
    W = st.sidebar.number_input("Width", value=1080, step=10, min_value=400)
    H = st.sidebar.number_input("Height", value=1080, step=10, min_value=400)
else:
    W, H = size_map[size_label]

# Brand colors & text
headline = st.text_input("Headline text", "Happy Diwali from XYZ Pipes!")
subtext = st.text_input("Subtext (optional)", "Special Festive Offers on Quality Pipes")
brand_color = st.color_picker("Headline color", "#FFFFFF")
shadow = st.checkbox("Add text shadow for contrast", value=True)

# ---- Inputs: prompt + assets
prompt = st.text_area("Describe the background you want (prompt)",
                      "Warm golden festive lights, soft bokeh, elegant and clean backdrop")

logo_file = st.file_uploader("Upload logo (PNG with transparency preferred)", type=["png", "jpg", "jpeg"])
pipe_file = st.file_uploader("Upload product image (pipe photo)", type=["png", "jpg", "jpeg"])

# Positions & scaling
st.subheader("Placement")
col1, col2 = st.columns(2)
with col1:
    logo_scale = st.slider("Logo width (% of canvas width)", 5, 40, 18)
    logo_pos = st.selectbox("Logo position", ["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right"])
with col2:
    pipe_scale = st.slider("Pipe width (% of canvas width)", 15, 70, 45)
    pipe_pos = st.selectbox("Pipe position", ["Left-Center", "Right-Center", "Bottom-Center"])

# Font (fallback to default if ttf not present)
font_path = None  # put a .ttf in the repo and set path if you like

def place_image(base, overlay, width_px, anchor="Top-Right", margin=20):
    # scale and paste RGBA
    w_ratio = width_px / overlay.width
    new_size = (int(overlay.width * w_ratio), int(overlay.height * w_ratio))
    o = overlay.convert("RGBA").resize(new_size, Image.LANCZOS)
    bx, by = base.size
    x, y = margin, margin

    if "Right" in anchor: x = bx - o.width - margin
    if "Bottom" in anchor: y = by - o.height - margin
    if "Left" in anchor and "Center" in anchor: y = (by - o.height)//2
    if "Right" in anchor and "Center" in anchor: y = (by - o.height)//2
    if anchor == "Bottom-Center":
        x = (bx - o.width)//2; y = by - o.height - margin
    base.alpha_composite(o, dest=(x, y))
    return base

def draw_text_multiline(img, text, y_frac, fill, font_size_ratio=0.07, shadow_on=True):
    if not text: return
    W, H = img.size
    try:
        fnt = ImageFont.truetype(font_path, int(W * font_size_ratio)) if font_path else ImageFont.load_default()
    except:
        fnt = ImageFont.load_default()
    draw = ImageDraw.Draw(img)
    # wrap rough
    max_w = int(W*0.9)
    lines, line, w = [], "", 0
    for word in text.split():
        t = (line + " " + word).strip()
        ww, _ = draw.textsize(t, font=fnt)
        if ww <= max_w:
            line = t
        else:
            lines.append(line); line = word
    if line: lines.append(line)
    total_h = sum(draw.textsize(l, font=fnt)[1] for l in lines) + (len(lines)-1)*6
    y = int(H*y_frac - total_h/2)
    for l in lines:
        tw, th = draw.textsize(l, font=fnt)
        x = (W - tw)//2
        if shadow_on:
            draw.text((x+2, y+2), l, font=fnt, fill=(0,0,0,160))
        # convert hex fill to rgba
        if isinstance(fill, str) and fill.startswith("#"):
            fill_rgba = tuple(int(fill[i:i+2], 16) for i in (1,3,5)) + (255,)
        else:
            fill_rgba = (255,255,255,255)
        draw.text((x, y), l, font=fnt, fill=fill_rgba)
        y += th + 6

def call_ai_background(prompt, width, height):
    """
    Replace this with your chosen provider.
    Example payload for a generic text-to-image API.
    """
    headers = {"Authorization": f"Bearer {AI_API_KEY}"} if AI_API_KEY else {}
    payload = {"prompt": prompt, "width": width, "height": height}
    try:
        r = requests.post(AI_API_URL, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        # Expect bytes or base64; here assume raw PNG bytes returned.
        return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except Exception as e:
        st.warning(f"AI generation failed ({e}). Falling back to plain background.")
        img = Image.new("RGBA", (width, height), (25,25,25,255))
        return img

if st.button("Generate Banner", type="primary"):
    if not prompt:
        st.error("Please enter a background prompt.")
    else:
        base = call_ai_background(prompt, W, H)

        # Place pipe & logo
        base = base.convert("RGBA")
        if pipe_file:
            pipe_img = Image.open(pipe_file)
            base = place_image(base, pipe_img, int(W * pipe_scale/100), anchor=pipe_pos)
        if logo_file:
            logo_img = Image.open(logo_file)
            base = place_image(base, logo_img, int(W * logo_scale/100), anchor=logo_pos)

        # Draw texts
        draw_text_multiline(base, headline, y_frac=0.18, fill=brand_color, font_size_ratio=0.075, shadow_on=shadow)
        draw_text_multiline(base, subtext,  y_frac=0.30, fill=brand_color, font_size_ratio=0.045, shadow_on=shadow)

        st.image(base, caption="Preview", use_column_width=True)

        buf = io.BytesIO()
        base.convert("RGB").save(buf, format="PNG")
        st.download_button("Download PNG", data=buf.getvalue(), file_name="banner.png", mime="image/png")

st.caption("Tip: Save a ‘template’ with your preferred positions/scales, then just swap the prompt for each festival.")
