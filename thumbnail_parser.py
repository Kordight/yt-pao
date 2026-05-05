from io import BytesIO
import hashlib
import os
import uuid
import time
import random

from PIL import Image
import requests

# User-agent rotation to avoid blocking
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
]

DOWNLOAD_COUNT = 0

def download_image(url, retry_count=0, max_retries=3):
    """Download image with rate limiting, user-agent rotation, and retry logic."""
    global DOWNLOAD_COUNT

    if retry_count > max_retries:
        print(f"Error downloading image: Max retries exceeded for {url}")
        return None
    
    DOWNLOAD_COUNT += 1

    # Add random delay to avoid rate limiting (about 1-3 seconds)
    delay = random.uniform(0.5, 2.0)
    time.sleep(delay)

    # Add a longer cooldown every 100 downloads to look less bot-like
    if DOWNLOAD_COUNT % 100 == 0:
        cooldown = random.uniform(5.0, 12.0)
        print(f"Thumbnail download cooldown: sleeping {cooldown:.1f}s after {DOWNLOAD_COUNT} requests")
        time.sleep(cooldown)
    
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        return response.content
    except requests.exceptions.Timeout:
        print(f"Timeout downloading image, retrying... (attempt {retry_count + 1}/{max_retries})")
        time.sleep(2 ** retry_count)  # Exponential backoff
        return download_image(url, retry_count + 1, max_retries)
    except requests.exceptions.ConnectionError:
        print(f"Connection error, retrying... (attempt {retry_count + 1}/{max_retries})")
        time.sleep(2 ** retry_count)
        return download_image(url, retry_count + 1, max_retries)
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
def save_image(image_content, file_name=None):
    if not image_content:
        return None

    os.makedirs('static/thumbnail_cache', exist_ok=True)
    if file_name is None:
        file_name = uuid.uuid4().hex + '.jpg'  # Generate a unique file name
    file_path = os.path.join('static', 'thumbnail_cache', file_name)

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