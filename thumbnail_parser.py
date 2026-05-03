from io import BytesIO
import hashlib
import os
import uuid

from PIL import Image
import requests

def download_image(url):
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # Check if the request was successful
        return response.content  # Return the image content as bytes
    except requests.RequestException as e:
        print(f"Error downloading image: {e}")
        return None
    
# Calculate SHA256 hash of the image content
def calculate_sha256(image_content):
    if not image_content:
        return None
    sha256_hash = hashlib.sha256()
    sha256_hash.update(image_content)
    return sha256_hash.hexdigest()

# Save image to disk as a real JPEG file
def save_image(image_content):
    if not image_content:
        return None

    os.makedirs('thumbnail_cache', exist_ok=True)
    file_name = uuid.uuid4().hex + '.jpg'  # Generate a unique file name
    file_path = os.path.join('thumbnail_cache', file_name)

    try:
        with Image.open(BytesIO(image_content)) as img:
            # JPEG does not support alpha channels.
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.save(file_path, format='JPEG', quality=95)
        return file_name
    except Exception as e:
        print(f"Error converting image to JPEG: {e}")
        return None