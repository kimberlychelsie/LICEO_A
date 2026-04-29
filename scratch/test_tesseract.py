import pytesseract
import os
from PIL import Image

p = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
print(f'Path exists: {os.path.exists(p)}')

pytesseract.pytesseract.tesseract_cmd = p
print(f'Cmd set to: {pytesseract.pytesseract.tesseract_cmd}')

try:
    version = pytesseract.get_tesseract_version()
    print(f'Tesseract version: {version}')
except Exception as e:
    print(f'Error getting version: {e}')

try:
    # Try a simple OCR on a blank image
    img = Image.new('RGB', (100, 100), color='white')
    text = pytesseract.image_to_string(img)
    print(f'OCR successful, output: "{text.strip()}"')
except Exception as e:
    print(f'Error performing OCR: {e}')
