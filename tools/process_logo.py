import sys
from PIL import Image
import numpy as np

def process_logo():
    # Input: Original high-res black logo on white background
    input_path = "/Users/dinu/.gemini/antigravity/brain/9711b9e3-9257-4e15-8895-360d54e41845/uploaded_image_1768498198997.png"
    
    print(f"Loading {input_path}...")
    try:
        img = Image.open(input_path).convert("RGBA")
        # User requested 180 degrees from previous (which was -90).
        # So we want +90 (Counter-Clockwise) relative to original.
        img = img.rotate(90, expand=True) 
        print("Rotated image 90 degrees COUNTER-clockwise.")
    except Exception as e:
        print(f"Error loading image: {e}")
        return

    # Convert to numpy array for fast processing
    data = np.array(img)
    
    # Extract RGB
    r, g, b, a = data.T
    
    # Logic: If pixel is light (white/grey), make it transparent.
    # If pixel is dark (black/grey), make it opaque.
    
    # Threshold: anything brighter than 200/255 is background.
    brightness = (r.astype(int) + g.astype(int) + b.astype(int)) / 3
    
    # Mask: True where pixel is DARK (Logo)
    logo_mask = brightness < 200 
    
    # --- Generate White Mask (for Header) ---
    # Color = White (255, 255, 255)
    # Alpha = 255 where mask is True, 0 otherwise
    
    white_img = np.zeros_like(data)
    white_img[..., 0] = 255 # R
    white_img[..., 1] = 255 # G
    white_img[..., 2] = 255 # B
    white_img[..., 3] = np.where(logo_mask, 255, 0) # A
    
    output_white = "frontend/public/logo-mask-v5.png"
    Image.fromarray(white_img).save(output_white)
    print(f"Saved White Mask: {output_white}")
    
    # --- Generate Black Icon (for Favicon) ---
    # Color = Black (0, 0, 0)
    # Alpha = 255 where mask is True, 0 otherwise
    
    black_img = np.zeros_like(data)
    black_img[..., 0] = 0 # R
    black_img[..., 1] = 0 # G
    black_img[..., 2] = 0 # B
    black_img[..., 3] = np.where(logo_mask, 255, 0) # A
    
    # Resize favicon to standard size (e.g. 64x64 or keep high res?)
    # Keep high res for now, let browser scale.
    
    output_black = "frontend/public/favicon-v5.png"
    Image.fromarray(black_img).save(output_black)
    print(f"Saved Black Icon: {output_black}")

if __name__ == "__main__":
    process_logo()
