
from PIL import Image, ImageDraw
import math
import os

ICON_DIR = "frontend/public/icons"
os.makedirs(ICON_DIR, exist_ok=True)

def draw_dot(filename, color, border_color=(255, 255, 255, 255), size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    padding = 4
    bbox = (padding, padding, size - padding, size - padding)
    
    # Draw Circle
    draw.ellipse(bbox, fill=color, outline=border_color, width=3)
    
    filepath = os.path.join(ICON_DIR, filename)
    img.save(filepath)
    print(f"Generated: {filepath}")

if __name__ == "__main__":
    # Pantone Wine Red (Approx #722F37 -> 114, 47, 55, 255)
    # Making it slightly brighter for visibility on dark globe: (160, 40, 60)
    draw_dot("capital_dot.png", color=(160, 40, 60, 255))

    # Sparkling Oyster Blue (Metallic Blue-Grey -> #60A5FA)
    # Close to Tailwind Blue-400: (96, 165, 250, 255)
    draw_dot("cluster_dot.png", color=(96, 165, 250, 255))
    
    # Keep the original generic blue dot just in case
    draw_dot("city_dot.png", color=(6, 182, 212, 255))
