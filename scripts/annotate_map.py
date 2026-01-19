from PIL import Image, ImageDraw
import sys

# Load Image
input_path = "/Users/dinu/.gemini/antigravity/brain/9711b9e3-9257-4e15-8895-360d54e41845/uploaded_image_1768739857601.png"
output_path = "frontend/public/about/clusters_annotated_v2.png"

try:
    img = Image.open(input_path)
except FileNotFoundError:
    print(f"Error: Could not find image at {input_path}")
    sys.exit(1)

draw = ImageDraw.Draw(img)

# Colors
COLOR_BLUE = "#3b82f6"   # Standard Blue
COLOR_CYAN = "#06b6d4"   # Cyan
COLOR_RED = "#be123c"    # Wine Red

# Helper to draw arrow
def draw_arrow(draw, start, end, color, width=3):
    # Draw line
    draw.line([start, end], fill=color, width=width)
    
    # Draw Arrowhead (Sharper)
    import math
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle = math.atan2(dy, dx)
    
    head_size = 12 # Smaller head
    angle1 = angle + math.pi - 0.4 # Sharper angle
    angle2 = angle + math.pi + 0.4
    
    p1 = (end[0] + head_size * math.cos(angle1), end[1] + head_size * math.sin(angle1))
    p2 = (end[0] + head_size * math.cos(angle2), end[1] + head_size * math.sin(angle2))
    
    # Draw filled polygon for head
    draw.polygon([end, p1, p2], fill=color)

# REFINED COORDINATES
# 1. Sibiu (Blue S): ~455, 498
# Arrow W->E. Start closer.
draw_arrow(draw, (390, 498), (445, 498), COLOR_BLUE, width=3)

# 2. Timisoara (Cyan T): ~235, 490
# Arrow E->W. Start closer.
draw_arrow(draw, (300, 490), (255, 490), COLOR_CYAN, width=3)

# 3. Bucharest (Red B): ~615, 600 (Top of the B circle is around 590, center ~610?)
# The previous arrow (North to South) "sliced" it. This means it went too far down.
# Let's stop HIGHER.
# Target: (615, 580) - Just above the B circle.
draw_arrow(draw, (620, 500), (620, 570), COLOR_RED, width=3)

# Save
img.save(output_path)
print(f"Annotated image saved to {output_path}")
