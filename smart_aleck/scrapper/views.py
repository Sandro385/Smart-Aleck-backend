from django.shortcuts import render, HttpResponse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


def scrap(request):
    # Open the webpage
    driver = open_webpage("https://matsne.gov.ge/en/document/search?page=1")  # Replace with your target URL
    
    # Wait for the page to load
    time.sleep(5)  # Adjust the sleep time as necessary
    
    # Close the driver
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
    for i in range(0, min(1, len(links))):

        links[i].click()
        print(f"clicked on button number {i+1}")
        scrape_page_data_with_bs4(driver.page_source)
        time.sleep(20)
        driver.find_element(By.CLASS_NAME, 'goback').click()
        print("clicked back button")
        
        time.sleep(10)

        links = driver.find_elements(By.CSS_SELECTOR, "div.panel-heading p a")
    
    return driver

def scrape_page_data_with_bs4(page_source):
    try:
        # Parse the page source with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')

        paragraphs = soup.find_all('p')
        scraped_data = [p.get_text() for p in paragraphs if p.get_text()!="\n"]

        # Print or return the scraped data
        for i, text in enumerate(scraped_data):
            print(text)

        return scraped_data
    
    except Exception as e:
        print(f"Error occurred while scraping: {str(e)}")
        return None