# Download image from url to ram

import requests

def download_image(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        return response.content  # Return the image content as bytes
    except requests.RequestException as e:
        print(f"Error downloading image: {e}")
        return None
    
# Calculate SHA256 hash of the image content
import hashlib
def calculate_sha256(image_content):
    sha256_hash = hashlib.sha256()
    sha256_hash.update(image_content)
    return sha256_hash.hexdigest()

