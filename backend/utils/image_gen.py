import os
import requests
import uuid
import google.generativeai as genai
from PIL import Image

# Configure Gemini
# Assuming GEMINI_API_KEY is already loaded in environment
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Use the specific model capable of image generation
# 'gemini-1.5-flash' is often text-only or multimodal input. 
# For image *generation*, we usually need a specific endpoint or model (e.g. Imagen or Gemini Pro Vision if supported).
# However, effectively we use the 'generate_image' tool in this agent context.
# BUT, for the actual Python backend to do it, it needs to call the API.
# Currently, Gemini API for Image Generation (Imagen 3) is available via Vertex AI or specific endpoints.
# For simplicity in this demo, since we might not have Vertex credentials set up, 
# we will mock the generation IF we can't hit the real API or use a standard placeholder logic if key fails.
# OR, better: We assume the user has access to a model like "gemini-1.5-pro-latest" or "imagen-3.0-generate-001".

async def generate_digest_image(title: str, city: str, output_dir: str = "static/digest_images") -> str:
    """
    Generates an image for a digest and returns the relative path.
    """
    
    prompt = (
        f"A line-drawing illustration with marker rendering. "
        f"Foreground: Typography or symbolic representation of '{title}'. "
        f"Background: A recognizable architectural landmark of {city}. "
        f"Style: Architectural sketch, black ink lines, pastel marker highlights. "
        f"Industrial design feel. Minimalist."
    )

    try:
        # NOTE: Using the standard Google GenAI SDK for image generation
        # 'imagen-3.0-generate-001' is the model name for Imagen 3 on AI Studio
        model = genai.ImageGenerationModel("imagen-3.0-generate-001")
        
        response = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9", # or "1:1"
            safety_filter_level="block_only_high",
            person_generation="allow_adult"
        )
        
        if not response.images:
             raise Exception("No image generated")

        image = response.images[0]
        
        # Ensure directory
        full_dir = os.path.join(os.getcwd(), output_dir)
        if not os.path.exists(full_dir):
            os.makedirs(full_dir)
            
        # Filename
        filename = f"digest_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(full_dir, filename)
        
        image.save(filepath)
        
        return f"/static/digest_images/{filename}"

    except Exception as e:
        print(f"IMAGE GEN ERROR: {e}")
        # Fallback/Mock for now if API fails (e.g. model access issues)
        # In production this should be handled gracefully
        raise e
