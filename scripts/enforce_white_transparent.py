import os
import resvg_py
from PIL import Image

EXT_MEDIA = r"g:\My Drive\helios\skelion_vscode_extension\media"
ARTIFACT_DIR = (
    r"C:\Users\adity\.gemini\antigravity\brain\eddfae2f-e0dc-4498-a908-e77d6173906d"
)

# 1. Update icon.svg to pure #FFFFFF
icon_path = os.path.join(EXT_MEDIA, "icon.svg")
with open(icon_path, "r", encoding="utf-8") as f:
    icon_content = f.read()

# Replace fill="currentColor" with fill="#FFFFFF"
icon_content_white = icon_content.replace('fill="currentColor"', 'fill="#FFFFFF"')
with open(icon_path, "w", encoding="utf-8") as f:
    f.write(icon_content_white)

with open(os.path.join(ARTIFACT_DIR, "icon.svg"), "w", encoding="utf-8") as f:
    f.write(icon_content_white)

print("Updated icon.svg to pure white (#FFFFFF) on transparent background")

# 2. Master White SVG (1024x1024) - Pure White on 100% Transparent background
white_svg_path = os.path.join(EXT_MEDIA, "skelion_logo_white.svg")
with open(white_svg_path, "r", encoding="utf-8") as f:
    white_svg_content = f.read()

# Ensure it's in artifact dir
with open(
    os.path.join(ARTIFACT_DIR, "skelion_logo_white.svg"), "w", encoding="utf-8"
) as f:
    f.write(white_svg_content)

# Render PNG: pure white on transparent RGBA
png_bytes_1024 = resvg_py.svg_to_bytes(
    svg_string=white_svg_content, width=1024, height=1024
)
png_bytes_512 = resvg_py.svg_to_bytes(
    svg_string=white_svg_content, width=512, height=512
)

# Save 1024x1024 PNG
for target_dir in [EXT_MEDIA, ARTIFACT_DIR]:
    with open(os.path.join(target_dir, "skelion_logo_white.png"), "wb") as f:
        f.write(png_bytes_1024)
    with open(os.path.join(target_dir, "skelion_logo_white_512.png"), "wb") as f:
        f.write(png_bytes_512)

# Verify transparency of generated PNG
img = Image.open(os.path.join(EXT_MEDIA, "skelion_logo_white.png"))
print(f"PNG mode: {img.mode}, size: {img.size}")
# Corner pixel should be (0, 0, 0, 0) or alpha = 0
corner_pixel = img.getpixel((0, 0))
print(f"Corner pixel (should have alpha 0): {corner_pixel}")
assert corner_pixel[3] == 0, "Corner pixel is not transparent!"

# Center-ish pixel that hits the white mark
# Check some non-transparent pixels to verify color is (255, 255, 255, 255)
white_pixels = [p for p in img.getdata() if p[3] > 200]
print(f"Sample white mark pixel: {white_pixels[0]}")
assert (
    white_pixels[0][0] == 255
    and white_pixels[0][1] == 255
    and white_pixels[0][2] == 255
), "Logo pixel is not pure white!"

# 3. Clean up non-white / non-transparent assets
remove_files = [
    "skelion_logo_black.svg",
    "skelion_logo_black.png",
    "skelion_logo_duotone_light.svg",
    "skelion_logo_duotone_light.png",
    "skelion_logo_duotone_dark.svg",
    "skelion_logo_duotone_dark.png",
]
for rf in remove_files:
    p1 = os.path.join(EXT_MEDIA, rf)
    p2 = os.path.join(ARTIFACT_DIR, rf)
    if os.path.exists(p1):
        os.remove(p1)
        print(f"Removed non-white file: {rf} from media")
    if os.path.exists(p2):
        os.remove(p2)
        print(f"Removed non-white file: {rf} from artifact")

print("All assets successfully configured to pure white and transparent!")
