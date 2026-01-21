import os
import httpx
import uuid
import base64

# ... (omitted comments)

async def generate_digest_image(title: str, city: str, output_dir: str = None, api_key: str = None) -> tuple[str, str]:
    """
    Generates an image for a digest and returns the relative path.
    Uses Imagen 4.0 Fast via REST API (Async).
    """
    # Determine output directory (Persistent or Local)
    data_dir = os.getenv("DATA_DIR")
    if not data_dir:
        if os.path.exists("/app/data"):
            data_dir = "/app/data"
        else:
            data_dir = "."
            
    relative_path = "static/digest_images"
    if output_dir is None:
        output_dir = os.path.join(data_dir, relative_path)
    
    # Configure API Key per request
    final_key = api_key or os.getenv("GEMINI_API_KEY")
    
    prompt = (
        f"An illustration capturing '{title}'. "
        f"The background shows an iconic landmark of {city}."
        f"Style: Architectural sketch, black ink lines, pastel marker highlights."
        f"Industrial design feel. Minimalist. Text should appear only if strictly necessary, and only within a valid illustrative context."
    )

    try:
        if not final_key:
             # Just raise to trigger fallback
             raise Exception("Missing API Key")

        # REST API for Imagen 4.0
        model = "imagen-4.0-ultra-generate-001"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={final_key}"
        
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": "16:9"}
        }
        
        print(f"Generating image with {model}...")
        
        # Async HTTP Request
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            
        if resp.status_code != 200:
            raise Exception(f"API Error {resp.status_code}: {resp.text}")
            
        data = resp.json()
        if 'predictions' not in data or not data['predictions']:
            raise Exception("No predictions returned")
            
        b64_data = data['predictions'][0]['bytesBase64Encoded']
        image_data = base64.b64decode(b64_data)
        
        # Ensure directory
        if os.path.isabs(output_dir):
            full_dir = output_dir
        else:
            full_dir = os.path.join(os.getcwd(), output_dir)

        if not os.path.exists(full_dir):
            os.makedirs(full_dir)
            
        # Filename
        filename = f"digest_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(full_dir, filename)
        
        print(f"IMAGE GEN: Saving to {filepath}")
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        return f"/{relative_path}/{filename}", prompt

    except Exception as e:
        print(f"IMAGE GEN ERROR: {e}")
        # Fallback: Generate a local placeholder image using PIL
        try:
            from PIL import Image, ImageDraw
            import random
            
            width, height = 1024, 576
            img = Image.new('RGB', (width, height), color=(20, 20, 30))
            draw = ImageDraw.Draw(img)
            
            for _ in range(10):
                x1 = random.randint(0, width)
                y1 = random.randint(0, height)
                x2 = random.randint(x1, width)
                y2 = random.randint(y1, height)
                draw.line([(x1, y1), (x2, y2)], fill=(50, 50, 80), width=2)
                
            # Ensure directory (Fallback)
            if os.path.isabs(output_dir):
                full_dir = output_dir
            else:
                full_dir = os.path.join(os.getcwd(), output_dir)

            if not os.path.exists(full_dir):
                os.makedirs(full_dir)
                
            filename = f"fallback_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(full_dir, filename)
            img.save(filepath)
            
            print(f"Generated fallback image: {filename}")
            return f"/{relative_path}/{filename}", "Fallback Placeholder (API Error)"
            
        except Exception as fallback_error:
            print(f"FALLBACK GEN ERROR: {fallback_error}")
            # Absolute safety net: Return a static asset that we know exists (copied in main.py)
            return "/static/placeholder_digest.png", "Error Placeholder"
