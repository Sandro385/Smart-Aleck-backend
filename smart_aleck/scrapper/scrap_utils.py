from datetime import datetime
import re, unicodedata
from .models import LawE, LawG
from django.http import JsonResponse
from django.utils import timezone

def save_data(scraped_data):
    try:
        created_at = timezone.make_aware(datetime.strptime(scraped_data["created_at"], '%d/%m/%Y'))
        # Create and save the Law instance
        law = LawG(
            law_name = scraped_data["law_name"],
            law_description = scraped_data["law_description"],
            registration_number = scraped_data["registration_number"],
            created_at = created_at
        )
        law.save()
        return JsonResponse({"success": True, "message": "Law data scraped and saved successfully."}, status=201)

    except Exception as e:
        print("Error : ",e)
        return JsonResponse({"success": False, "message": str(e)}, status=400)

def split_text(text, chunk_size=2048):
    """
    Splits the text into chunks of a specified size for creating embeddings.
    Adjust the chunk_size based on your data.
    """
    sentences = text.split('.')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < chunk_size:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "

    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def batch_vectors(vectors, batch_size=100):
    for i in range(0, len(vectors), batch_size):
        yield vectors[i:i+batch_size]


def clean_parsed_data(data):
    """
    Cleans the parsed HTML data by removing unnecessary characters, newlines, tabs,
    and normalizing the text. Keeps Georgian characters and single newlines.
    
    Parameters:
    data (str): The raw text extracted from the parsed HTML.
    
    Returns:
    str: Cleaned text with single newlines between paragraphs.
    """
    # 1. Replace multiple newlines with a single newline
    cleaned_data = re.sub(r'\n+', '\n', data)  # Replace multiple newlines with a single newline
    
    # 2. Remove unnecessary tabs and spaces around the newlines
    cleaned_data = re.sub(r'[ \t]+', ' ', cleaned_data)  # Replace multiple spaces/tabs with a single space
    cleaned_data = re.sub(r' *\n *', '\n', cleaned_data)  # Clean spaces around newlines
    
    # 3. Normalize Unicode characters but keep Georgian text and other non-ASCII
    cleaned_data = unicodedata.normalize('NFKC', cleaned_data)  # Normalize characters without removing non-ASCII ones
    
    # 4. Optionally, remove unwanted punctuation or symbols (customizable)
    cleaned_data = re.sub(r'[^\w\s,.!?\'-Ⴀ-ჿ]', '', cleaned_data)  # Allow Georgian Unicode range (U+10A0 to U+10FF)

    return cleaned_data