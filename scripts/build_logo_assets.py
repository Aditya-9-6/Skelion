import os
import cv2
import numpy as np
import potrace
import resvg_py
from PIL import Image

SRC_IMG = r'C:/Users/adity/.gemini/antigravity/brain/eddfae2f-e0dc-4498-a908-e77d6173906d/.user_uploaded/media_1793538427613_5c0214ff.jpg'
EXT_MEDIA = r'g:\My Drive\helios\skelion_vscode_extension\media'
ARTIFACT_DIR = r'C:\Users\adity\.gemini\antigravity\brain\eddfae2f-e0dc-4498-a908-e77d6173906d'
SCRATCH_DIR = r'g:\My Drive\helios\scratch'

os.makedirs(EXT_MEDIA, exist_ok=True)
os.makedirs(SCRATCH_DIR, exist_ok=True)

img = cv2.imread(SRC_IMG)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
diff = 255 - gray
_, mask = cv2.threshold(diff, 28, 255, cv2.THRESH_BINARY)
kernel = np.ones((2, 2), np.uint8)
clean_mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

# Trace overall silhouette
data_all = (clean_mask > 0).astype(bool)
bmp_all = potrace.Bitmap(data_all)
path_all = bmp_all.trace(alphamax=1.0, opttolerance=0.2)
curves_all = path_all[1:] # curve 0 is image border

def get_pts(curves):
    pts = []
    for c in curves:
        pts.append(c.start_point)
        for s in c:
            if s.is_corner:
                pts.extend([s.c, s.end_point])
            else:
                pts.extend([s.c1, s.c2, s.end_point])
    return pts

all_pts = get_pts(curves_all)
min_x = min(p.x for p in all_pts)
max_x = max(p.x for p in all_pts)
min_y = min(p.y for p in all_pts)
max_y = max(p.y for p in all_pts)
logo_w = max_x - min_x
logo_h = max_y - min_y
cx = (min_x + max_x) / 2.0
cy = (min_y + max_y) / 2.0

def curve_to_svg_d(curve, scale=1.0, dx=0.0, dy=0.0):
    d = []
    sx = curve.start_point.x * scale + dx
    sy = curve.start_point.y * scale + dy
    d.append(f"M {sx:.2f} {sy:.2f}")
    for seg in curve:
        if seg.is_corner:
            cx_ = seg.c.x * scale + dx
            cy_ = seg.c.y * scale + dy
            ex_ = seg.end_point.x * scale + dx
            ey_ = seg.end_point.y * scale + dy
            d.append(f"L {cx_:.2f} {cy_:.2f} L {ex_:.2f} {ey_:.2f}")
        else:
            c1x = seg.c1.x * scale + dx
            c1y = seg.c1.y * scale + dy
            c2x = seg.c2.x * scale + dx
            c2y = seg.c2.y * scale + dy
            ex_ = seg.end_point.x * scale + dx
            ey_ = seg.end_point.y * scale + dy
            d.append(f"C {c1x:.2f} {c1y:.2f} {c2x:.2f} {c2y:.2f} {ex_:.2f} {ey_:.2f}")
    d.append("Z")
    return " ".join(d)

# 1. VS Code Extension Icon (24x24 viewBox)
target_size_24 = 19.0
scale_24 = target_size_24 / max(logo_w, logo_h)
dx_24 = 12.0 - cx * scale_24
dy_24 = 12.0 - cy * scale_24
d_24 = " ".join([curve_to_svg_d(c, scale_24, dx_24, dy_24) for c in curves_all])

vscode_icon_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none">
  <!-- Skelion Geometric Shield Monogram Activity Bar Icon -->
  <path d="{d_24}" fill="currentColor" fill-rule="evenodd"/>
</svg>
'''
# Save to extension media
ext_icon_path = os.path.join(EXT_MEDIA, "icon.svg")
with open(ext_icon_path, "w", encoding="utf-8") as f:
    f.write(vscode_icon_svg)
print(f"Updated VS Code extension icon: {ext_icon_path}")

# 2. Master Vector (1024x1024)
target_size_master = 820.0
scale_master = target_size_master / max(logo_w, logo_h)
dx_master = 512.0 - cx * scale_master
dy_master = 512.0 - cy * scale_master
d_master = " ".join([curve_to_svg_d(c, scale_master, dx_master, dy_master) for c in curves_all])

# Master Black SVG (transparent)
svg_black = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024" fill="none">
  <path d="{d_master}" fill="#000000" fill-rule="evenodd"/>
</svg>
'''
# Master White SVG (transparent)
svg_white = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024" fill="none">
  <path d="{d_master}" fill="#FFFFFF" fill-rule="evenodd"/>
</svg>
'''

# 3. Two-Tone Faceted Version
# Trace amber and gold facets separately
amber_mask = (clean_mask > 0) & (gray < 180)
gold_mask = (clean_mask > 0) & (gray >= 180)

# clean masks
amber_clean = cv2.morphologyEx(amber_mask.astype(np.uint8) * 255, cv2.MORPH_OPEN, kernel) > 0
gold_clean = cv2.morphologyEx(gold_mask.astype(np.uint8) * 255, cv2.MORPH_OPEN, kernel) > 0

bmp_amber = potrace.Bitmap(amber_clean)
bmp_gold = potrace.Bitmap(gold_clean)
path_amber = bmp_amber.trace(alphamax=1.0, opttolerance=0.2)
path_gold = bmp_gold.trace(alphamax=1.0, opttolerance=0.2)

d_amber_master = " ".join([curve_to_svg_d(c, scale_master, dx_master, dy_master) for c in path_amber[1:]])
d_gold_master = " ".join([curve_to_svg_d(c, scale_master, dx_master, dy_master) for c in path_gold[1:]])

# Duotone Black & Slate (Light background friendly)
svg_duotone_light = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024" fill="none">
  <g fill-rule="evenodd">
    <!-- Dark Amber Facets -> Solid Charcoal/Black -->
    <path d="{d_amber_master}" fill="#09090B"/>
    <!-- Bright Gold Facets -> Cool Slate / Medium Gray -->
    <path d="{d_gold_master}" fill="#71717A"/>
  </g>
</svg>
'''

# Duotone White & Zinc (Dark background friendly)
svg_duotone_dark = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024" fill="none">
  <g fill-rule="evenodd">
    <!-- Dark Amber Facets -> Light Zinc Gray -->
    <path d="{d_amber_master}" fill="#A1A1AA"/>
    <!-- Bright Gold Facets -> Bright White -->
    <path d="{d_gold_master}" fill="#FFFFFF"/>
  </g>
</svg>
'''

# Save all SVGs to ext_media and artifact dir
files_to_save = {
    "skelion_logo_black.svg": svg_black,
    "skelion_logo_white.svg": svg_white,
    "skelion_logo_duotone_light.svg": svg_duotone_light,
    "skelion_logo_duotone_dark.svg": svg_duotone_dark,
}

for name, content in files_to_save.items():
    p1 = os.path.join(EXT_MEDIA, name)
    p2 = os.path.join(ARTIFACT_DIR, name)
    with open(p1, "w", encoding="utf-8") as f:
        f.write(content)
    with open(p2, "w", encoding="utf-8") as f:
        f.write(content)

# Render PNGs using resvg-py
png_renders = [
    ("skelion_logo_black.png", svg_black, 1024, 1024),
    ("skelion_logo_white.png", svg_white, 1024, 1024),
    ("skelion_logo_duotone_light.png", svg_duotone_light, 1024, 1024),
    ("skelion_logo_duotone_dark.png", svg_duotone_dark, 1024, 1024),
]

for name, svg_str, w, h in png_renders:
    b = resvg_py.svg_to_bytes(svg_string=svg_str, width=w, height=h)
    p1 = os.path.join(EXT_MEDIA, name)
    p2 = os.path.join(ARTIFACT_DIR, name)
    with open(p1, "wb") as f:
        f.write(b)
    with open(p2, "wb") as f:
        f.write(b)
    print(f"Generated PNG: {name}")

# Also copy source images to artifact dir for side-by-side display
from shutil import copyfile
copyfile(SRC_IMG, os.path.join(ARTIFACT_DIR, "original_logo_yellow.jpg"))
copyfile(r"C:/Users/adity/.gemini/antigravity/brain/eddfae2f-e0dc-4498-a908-e77d6173906d/.user_uploaded/media_1793538394703_146fe754.png", os.path.join(ARTIFACT_DIR, "old_activity_bar_icon.png"))
copyfile(ext_icon_path, os.path.join(ARTIFACT_DIR, "icon.svg"))

print("All assets generated and exported successfully!")
