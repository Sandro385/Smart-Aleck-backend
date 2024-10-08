from django.shortcuts import render, HttpResponse
from selenium import webdriver
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, os
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from .scrap_utils import save_data, split_text, batch_vectors
from .models import Law
from pinecone.grpc import PineconeGRPC as Pinecone
from sentence_transformers import SentenceTransformer
import torch
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from openai import OpenAI
from rest_framework.response import Response

load_dotenv()


def scrap(request):
    for i in range(1, 26):
        driver = open_webpage(f"https://matsne.gov.ge/en/document/search?page={i}")  # Replace with your target URL
        time.sleep(5)  # Adjust the sleep time as necessary
        driver.quit()

    return HttpResponse("Scraping complete!")


def open_webpage(url):
    # Set up Chrome options (no headless mode since you want to see it working)
    options = Options()
    options.add_argument("--no-sandbox")  # Needed for some environments
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

    # Create a new instance of the Chrome driver
    service = Service('/usr/local/bin/chromedriver')  # Replace with the path to your ChromeDriver
    driver = webdriver.Chrome(service=service, options=options)
    
    # Open the webpage
    driver.get(url)
    
    links = driver.find_elements(By.CSS_SELECTOR, "div.panel-heading p a")
    print("total number of buttons : ", len(links))

    for i in range(0, min(21, len(links))):

        links[i].click()
        print(f"clicked on button number {i+1}")
        time.sleep(3)

        registration_code = driver.find_element(By.XPATH, "//td[text()='Registration code']/following-sibling::td").text
        date_of_issue = driver.find_element(By.XPATH, "//td[text()='Date of issuing']/following-sibling::td").text

        response=scrape_page_data_with_bs4(driver.page_source, registration_code, date_of_issue)
        print(response)
        time.sleep(5)

        driver.find_element(By.CLASS_NAME, 'goback').click()
        print("clicked back button")
        print()
        time.sleep(5)

        links = driver.find_elements(By.CSS_SELECTOR, "div.panel-heading p a")

    return driver

def scrape_page_data_with_bs4(page_source, registration_code, date_of_issue):
    try:
        # Parse the page source with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')

        paragraphs = soup.find_all('p')
        
        title_tag = soup.find('h1', class_='page-header')
        if title_tag:
            title = title_tag.get_text().replace('\n', ' ').strip()
        else:
            title = None
        
        scraped_data = [p.get_text() for p in paragraphs if p.get_text()!="\n"]

        print("law title : ",title)
        print("Registration code : ",registration_code)
        print("Date of issue : ",date_of_issue)

        full_text=""
        for i, text in enumerate(scraped_data):
            if i>4:
                full_text+=text

        # with open(f"{title}.txt", "w") as file:
        #     file.write(full_text)
        
        data = {
            "law_name": title,
            "law_description": full_text,
            "registration_number": registration_code, 
            "created_at": date_of_issue  
        }
        response = save_data(scraped_data = data)
        return response
    
    except Exception as e:
        print(f"Error occurred while scraping: {str(e)}")
        return None
    

class PineUpsertAPI(APIView):
    def post(self, request, chunk_size=10):
        # Initialize model once
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = SentenceTransformer('hli/lstm-qqp-sentence-transformer')  # LSTM model you're using
        model.to(device)

        # Initialize Pinecone client and index
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index = pc.Index(os.getenv('PINECONE_INDEX'))

        offset = 0
        while True:
            # Fetch a chunk of law objects at a time
            laws = Law.objects.order_by('id')[offset:offset + chunk_size]

            # If no laws are returned, break the loop
            if not laws:
                break

            # Process each law in the current chunk
            for i, law in enumerate(laws):
                print(f"Law Count: {i+1}")
                print(f"Law ID: {law.id} | Law Name: {law.law_name} | Registration Number: {law.registration_number} | Created At: {law.created_at}")
                print("-----------------------------------------------------------------------------")

                # Split law description into chunks
                text_chunks = split_text(law.law_description)

                # Filter out empty chunks
                text_chunks = [chunk for chunk in text_chunks if chunk.strip()]
                if not text_chunks:
                    print(f"No valid text chunks for law: {law.law_name} (ID: {law.id})")
                    continue

                try:
                    # Generate embeddings for the valid chunks using the LSTM model
                    chunk_embeddings = model.encode(text_chunks, convert_to_tensor=True)
                    print(f"Encoding done for law ID: {law.id}, length of first embedding: {len(chunk_embeddings[0])}")

                    # Prepare vectors for Pinecone
                    vectors = [
                        (f'chunk-{i}', embedding.cpu().numpy(), {'text': chunk, 'registration_code': str(law.registration_number)})
                        for i, (embedding, chunk) in enumerate(zip(chunk_embeddings, text_chunks))
                    ]
                    print(f"Vectors prepared for law ID: {law.id}")

                    # Upload vectors in batches
                    batch_size = 200
                    for vector_batch in batch_vectors(vectors, batch_size=batch_size):
                        try:
                            print(f"Starting upsert for law ID: {law.id}")
                            index.upsert(vectors=vector_batch, namespace="combined")
                            print(f"Upsert done for law ID: {law.id}")
                        except Exception as e:
                            print(f"Error uploading batch for law ID: {law.id}: {str(e)}")
                            return Response({'error': str(e)}, status=500)

                except RuntimeError as e:
                    print(f"Error encoding text for law ID: {law.id}: {str(e)}")
                    return Response({'error': str(e)}, status=500)

            # Update offset to fetch the next batch of laws
            offset += chunk_size

        return Response({"message": "Data uploaded to Pinecone successfully!"}, status=200)



class SimpleQueryAPI(APIView):

    def post(self, request):
        query = request.data.get('query')
        # session_id = request.data.get('session_id')  # Uncomment if session_id is needed

        if not query:
            return Response({"error": "Query is required"}, status=status.HTTP_400_BAD_REQUEST)

        # if session_id is None:  # Uncomment if session_id validation is needed
            # return Response({"error": "Session ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            response_text = self.get_response(query)
            return Response({"response": response_text}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_response(self, query):
        """
        Gets the response based on the user's query using embeddings and Pinecone.
        """
        try:
            # Load the model
            model = SentenceTransformer('hli/lstm-qqp-sentence-transformer')
            device = torch.device('cpu')
            model.to(device)
            
            # Step 1: Encode the query to get embeddings
            chunk_embeddings = model.encode(query, convert_to_tensor=True)
            
            # Step 2: Initialize Pinecone and search for relevant embeddings
            pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
            index = pc.Index(os.getenv('PINECONE_INDEX'))
            index_stats = index.describe_index_stats()

            # namespace_stats = index_stats['namespaces'].get("combined", {})
            # num_chunks_in_namespace = namespace_stats.get('vector_count', 0)
            # top_k = min(10, num_chunks_in_namespace)

            # Step 3: Perform a similarity search using cosine similarity
            search_result = index.query(
                vector=chunk_embeddings,
                top_k=10,
                include_values=False,
                include_metadata=True,
                namespace="combined"
            )
            
            # print(search_result)
            # Gather the full text from the search results
            full_text = [
            {
                "registration_code": None,
                "text": result['metadata']['text']
            } 
            for result in search_result['matches']
        ]

            return full_text  # Return the list of texts directly

        except Exception as e:
            raise Exception(f"Error in get_response: {str(e)}")  # Raise a new exception with a message