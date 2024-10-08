from datetime import datetime
import re
from .models import Law
from django.http import JsonResponse
from django.utils import timezone

def save_data(scraped_data):
    try:
        created_at = timezone.make_aware(datetime.strptime(scraped_data["created_at"], '%d/%m/%Y'))
        # Create and save the Law instance
        law = Law(
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

def split_text(text, chunk_size=512):
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
