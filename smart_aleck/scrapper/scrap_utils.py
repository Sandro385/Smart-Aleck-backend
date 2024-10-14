from datetime import datetime
import re, unicodedata, os
from .models import LawE, LawG
from django.http import JsonResponse
from django.utils import timezone
from openai import OpenAI

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

def split_text(text, chunk_size=1024):
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


def refine_text_openai(chunks, query):
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Dynamically create the relevant chunks section
    if chunks:
        chunk_list = "\n\n".join([f"Chunks number : {i+1}. {chunk}" for i, chunk in enumerate(chunks)])
    else:
        chunk_list = "NO RELEVANT CHUNKS"

    print("chunks_list")
    print(chunk_list)
    # Create the prompt using the last 5 chats and summary
    message_to_send = [
    {
      "role": "system",
      "content": "You are an AI language model that uses the following text chunks as context to answer a question. Consider the information from all the chunks to provide a comprehensive and accurate answer."
    },
    {
      "role": "user",
      "content": "I have several chunks of text in the Georgian language. I will give you both the chunks and a question. Please answer the question based on the information in the chunks."
    },
    {
      "role": "user",
      "content": f"Question: {query}."
    },
    {
      "role": "user",
      "content": f"Chunks:\n{chunk_list}."
    }
  ]
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=message_to_send
    )
    
    return response.choices[0].message.content