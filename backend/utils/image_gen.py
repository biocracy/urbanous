import os
import requests
import uuid
import base64

# Configure Gemini
# Assuming GEMINI_API_KEY is already loaded in environment
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Use the specific model capable of image generation
# 'gemini-1.5-flash' is often text-only or multimodal input. 
# For image *generation*, we usually need a specific endpoint or model (e.g. Imagen or Gemini Pro Vision if supported).
# However, effectively we use the 'generate_image' tool in this agent context.
# BUT, for the actual Python backend to do it, it needs to call the API.
# Currently, Gemini API for Image Generation (Imagen 3) is available via Vertex AI or specific endpoints.
# For simplicity in this demo, since we might not have Vertex credentials set up, 
# we will mock the generation IF we can't hit the real API or use a standard placeholder logic if key fails.
# OR, better: We assume the user has access to a model like "gemini-1.5-pro-latest" or "imagen-3.0-generate-001".

async def generate_digest_image(title: str, city: str, output_dir: str = None, api_key: str = None) -> tuple[str, str]:
    """
    Generates an image for a digest and returns the relative path.
    Uses Imagen 4.0 Fast via REST API.
    """
    # Determine output directory (Persistent or Local)
    data_dir = os.getenv("DATA_DIR", ".")
    # Ideally images go to DATA_DIR/static/digest_images or similar.
    # But to keep URLs consistent (/static/...) we need to map it carefully.
    
    # If DATA_DIR is set (e.g. /app/data), we save to /app/data/static/digest_images
    # Then main.py must mount /app/data/static as /static
    
    relative_path = "static/digest_images"
    if output_dir is None:
        output_dir = os.path.join(data_dir, relative_path)
    
    # Configure API Key per request
    final_key = api_key or os.getenv("GEMINI_API_KEY")
    
    if not final_key:
         print("WARNING: No Gemini API Key provided for Image Gen. Falling back to placeholder.")
    
    prompt = (
        f"An illustration capturing '{title}'. "
        f"The background shows an iconic landmark of {city}."
        f"Style: Architectural sketch, black ink lines, pastel marker highlights."
        f"Industrial design feel. Minimalist."
    )

    try:
        if not final_key:
             raise Exception("Missing API Key")

        # REST API for Imagen 4.0
        # By pass deprecated/broken SDK
        # Using Ultra as requested for "Pro" quality
        model = "imagen-4.0-ultra-generate-001"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={final_key}"
        
        payload = {
            "instances": [
                {"prompt": prompt}
            ],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "16:9"
            }
        }
        
        print(f"Generating image with {model}...")
        resp = requests.post(url, json=payload, timeout=30)
        
        if resp.status_code != 200:
            raise Exception(f"API Error {resp.status_code}: {resp.text}")
            
        data = resp.json()
        if 'predictions' not in data or not data['predictions']:
            raise Exception("No predictions returned")
            
        b64_data = data['predictions'][0]['bytesBase64Encoded']
        image_data = base64.b64decode(b64_data)
        
        # Ensure directory
        full_dir = os.path.join(os.getcwd(), output_dir)
        if not os.path.exists(full_dir):
            os.makedirs(full_dir)
            
        # Filename
        filename = f"digest_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(full_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        return f"/{output_dir}/{filename}", prompt

    except Exception as e:
        print(f"IMAGE GEN ERROR: {e}")
        # Fallback: Generate a local placeholder image using PIL
        try:
            from PIL import Image, ImageDraw
            import random
            
            # Create a cool abstract gradient or dark background
            width, height = 1024, 576
            img = Image.new('RGB', (width, height), color=(20, 20, 30))
            draw = ImageDraw.Draw(img)
            
            # Draw some random architectural lines
            for _ in range(10):
                x1 = random.randint(0, width)
                y1 = random.randint(0, height)
                x2 = random.randint(x1, width)
                y2 = random.randint(y1, height)
                draw.line([(x1, y1), (x2, y2)], fill=(50, 50, 80), width=2)
                
            # Ensure directory
            full_dir = os.path.join(os.getcwd(), output_dir)
            if not os.path.exists(full_dir):
                os.makedirs(full_dir)
                
            filename = f"fallback_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(full_dir, filename)
            img.save(filepath)
            
            print(f"Generated fallback image: {filename}")
            return f"/{output_dir}/{filename}", "Fallback Placeholder (No Prompt)"
            
        except Exception as fallback_error:
            print(f"FALLBACK GEN ERROR: {fallback_error}")
            return "/static/placeholder_digest.png", "Error Placeholder" # valid static file fallback
