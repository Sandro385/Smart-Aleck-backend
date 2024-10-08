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
    

def pine_upsert(request, chunk_size=10):
    offset = 0
    while True:
        # Use LIMIT and OFFSET to fetch a chunk of 10 objects at a time
        laws = Law.objects.order_by('id')[offset:offset + chunk_size]

        # If no laws are returned, break the loop
        if not laws:
            break

        # Print each law object in the current chunk
        for law in laws:
            print(f"Law Name: {law.law_name}, Description: law.law_description, "
                  f"Registration Number: {law.registration_number}, Created At: {law.created_at}")
            print("-----------------------------------------------------------------------------")
            
            text_chunks=split_text(law.law_description)
         
            model = SentenceTransformer('all-distilroberta-v1')
            device = torch.device('cpu')
            model.to(device)
            
            chunk_embeddings = model.encode(text_chunks, convert_to_tensor=True)
            
            #upload embeddings with file_id to pinecone-db
            pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
            index = pc.Index(os.getenv('PINECONE_INDEX'))
            
            vectors = [(f'chunk-{i}', embedding, {'text': chunk}) for i, (embedding, chunk) in enumerate(zip(chunk_embeddings, text_chunks))]

            batch_size = 200
            for vector_batch in batch_vectors(vectors, batch_size=batch_size):
                try:
                    index.upsert(vectors=vector_batch, namespace=str(law.registration_number))
                    # logger.info(f"Uploaded batch of embeddings for file: {file_info.file_id}")
                except Exception as e:
                    print(f"Error uploading batch: {str(e)}")
                    # logger.error(f"Error uploading batch embeddings for file {file_info.file_id}: {e}")
                    raise

        # Update offset to fetch the next batch of 10
        offset += chunk_size
    return HttpResponse("Done")