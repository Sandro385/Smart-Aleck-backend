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
from .scrap_utils import save_data, split_text, batch_vectors, clean_parsed_data
from pinecone.grpc import PineconeGRPC as Pinecone
from sentence_transformers import SentenceTransformer
import torch
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from openai import OpenAI
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.http import JsonResponse
from .models import LawG


load_dotenv()


@api_view(['GET'])
def scrap(request):
    """
    A REST API endpoint to perform web scraping across multiple pages.
    """
    try:
        for i in range(1, 26):
            # Open the webpage using a utility function (make sure open_webpage is defined)
            driver = open_webpage(f"https://matsne.gov.ge/ka/document/search?type=all&sort=publishDate_desc&additional_status=normative&page={i}")
            
            # Introduce a delay to prevent overwhelming the server
            time.sleep(5)
            
            # Close the browser instance
            driver.quit()
        
        # Return success response
        return JsonResponse({'message': 'Scraping complete!', 'status': 'success'}, status=200)

    except Exception as e:
        # Return error response in case of failure
        return JsonResponse({'message': str(e), 'status': 'error'}, status=500)



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

        # registration_code = driver.find_element(By.XPATH, "//td[text()='Registration code']/following-sibling::td").text #english
        registration_code = driver.find_element(By.XPATH, "//td[text()='სარეგისტრაციო კოდი']/following-sibling::td").text # georgian
        # date_of_issue = driver.find_element(By.XPATH, "//td[text()='Date of issuing']/following-sibling::td").text #english
        date_of_issue = driver.find_element(By.XPATH, "//td[text()='მიღების თარიღი']/following-sibling::td").text #georgian

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

        cleaned_data=clean_parsed_data(full_text)

        # with open(f"{title}_1.txt", "w") as file:
        #     file.write(full_text)
        # with open(f"{title}_2.txt", "w") as file:
        #     file.write(cleaned_data)

        
        data = {
            "law_name": title,
            "law_description": cleaned_data,
            "registration_number": registration_code, 
            "created_at": date_of_issue  
        }
        response = save_data(scraped_data = data)
        return response
        # return "true"

    except Exception as e:
        print(f"Error occurred while scraping: {str(e)}")
        return None
    

class PineUpsertAPI(APIView):
    def post(self, request, chunk_size=10):
        # Initialize model once
        # device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # model = SentenceTransformer("distilbert-base-multilingual-cased")  # LSTM model you're using
        # model.to(device)

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Initialize Pinecone client and index
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index = pc.Index(os.getenv('PINECONE_INDEX'))

        offset = 0
        while True:
            # Fetch a chunk of law objects at a time
            laws = LawG.objects.order_by('registration_number')[offset:offset + chunk_size]

            # If no laws are returned, break the loop
            if not laws:
                break

            # Process each law in the current chunk
            for i, law in enumerate(laws):
                print(f"Law Count: {i+1}")
                print(f"Law Name: {law.law_name} | Registration Number: {law.registration_number} | Created At: {law.created_at}")
                print("-----------------------------------------------------------------------------")

                # Split law description into chunks
                text_chunks = split_text(law.law_description)

                # Filter out empty chunks
                text_chunks = [chunk for chunk in text_chunks if chunk.strip()]
                if not text_chunks:
                    print(f"No valid text chunks for law: {law.law_name})")
                    continue

                try:
                    # Generate embeddings for the valid chunks using the LSTM model
                    response = client.embeddings.create(input=text_chunks, model="text-embedding-3-large")
                    chunk_embeddings = [item.embedding for item in response.data]
                    print(f"length of first embedding: {len(chunk_embeddings[0])}")

                    # Prepare vectors for Pinecone
                    vectors = [
                        (f'chunk-{i}', embedding, {'text': chunk, 'registration_code': str(law.registration_number)})
                        for i, (embedding, chunk) in enumerate(zip(chunk_embeddings, text_chunks))
                    ]
                    

                    # Upload vectors in batches
                    batch_size = 200
                    for vector_batch in batch_vectors(vectors, batch_size=batch_size):
                        try:
                            # print(f"Starting upsert for law ID: {law.id}")
                            index.upsert(vectors=vector_batch, namespace=law.registration_number)
                            # print(f"Upsert done for law ID: {law.id}")
                        except Exception as e:
                            # print(f"Error uploading batch for law ID: {law.id}: {str(e)}")
                            return Response({'error': str(e)}, status=500)

                except RuntimeError as e:
                    # print(f"Error encoding text for law ID: {law.id}: {str(e)}")
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
            # model = SentenceTransformer('distilbert-base-multilingual-cased')
            # device = torch.device('cpu')
            # model.to(device)
            
            # Step 1: Encode the query to get embeddings
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            chunk_embeddings = client.embeddings.create(input=query, model="text-embedding-3-large").data[0].embedding
            
            # Step 2: Initialize Pinecone and search for relevant embeddings
            pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
            index = pc.Index(os.getenv('PINECONE_INDEX'))
            index_stats = index.describe_index_stats()
            
            all_namespaces = list(index_stats['namespaces'].keys())

            search_results = []
            for namespace in all_namespaces:
                try:
                                       
                    # Search within each namespace (file)
                    result = index.query(
                        namespace=namespace,
                        vector=chunk_embeddings,
                        top_k=2,
                        include_values=False,
                        include_metadata=True,
                    )
                    search_results.append(result['matches'])
                except Exception as e:
                    print(f"Skipping namespace {namespace} due to error: {str(e)}")

            # print(search_results)

            # Filter results based on the threshold
            filtered_results = []
            similarity_threshold=0.4

            # Loop through search_results to check scores and store texts with their scores
            for object in search_results:
                for result in object:
                    if 'score' in result and result['score'] >= similarity_threshold:  # Check if score exists and meets the threshold
                        # Append the text and score to filtered_results if text exists
                        if 'metadata' in result and 'text' in result['metadata']:
                            text = result['metadata']['text']
                            score = result['score']
                            print("score : ",score)
                            filtered_results.append({'text': text, 'score': score})

            print(len(filtered_results))
            # print(filtered_results)
            filtered_results.sort(key=lambda x: x['score'], reverse=True)
            return filtered_results  # Return the list of texts directly

        except Exception as e:
            raise Exception(f"Error in get_response: {str(e)}")  # Raise a new exception with a message