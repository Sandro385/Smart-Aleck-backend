from django.shortcuts import render, HttpResponse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Create your views here.
# Create your views here.
def scrap(request):
    # Open the webpage
    driver = open_webpage("https://matsne.gov.ge/en/document/search?page=1")  # Replace with your target URL
    
    # Wait for the page to load
    time.sleep(5)  # Adjust the sleep time as necessary

    # Click on the fourth link in the panel heading
    click_elements_in_sequence(driver)
    
    # Close the driver
    driver.quit()
    return HttpResponse("Scraping complete!")

def open_webpage(url):
    # Set up Chrome options
    options = Options()
    options.add_argument("--no-sandbox")  # Needed for some environments
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

    # Create a new instance of the Chrome driver
    service = Service('/usr/local/bin/chromedriver')  # Replace with the path to your ChromeDriver
    driver = webdriver.Chrome(service=service, options=options)
    
    # Open the webpage
    driver.get(url)
    
    return driver

def click_elements_in_sequence(driver):
    try:
        # Use a CSS selector to find all <a> elements within the specified structure
        links = driver.find_elements(By.CSS_SELECTOR, "div.panel-heading p a")
        
        # Iterate through elements from the 4th to the 23rd (index 3 to 22)
        for i in range(3, min(23, len(links))):
            # Click the element
            links[i].click()
            print(f"Clicked on element {i+1}: {links[i].text}")
            
            # Wait 5 seconds after clicking
            time.sleep(5)
            
            # Find the "Return back" button using its unique CSS selector and click it
            return_back = driver.find_element(By.CSS_SELECTOR, "a.goback")
            return_back.click()
            
            # Wait for the page to load after returning back
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.panel-heading p a"))
            )
            
            # Re-fetch the list of links (in case the page refreshes after navigation)
            links = driver.find_elements(By.CSS_SELECTOR, "div.panel-heading p a")
    
    except Exception as e:
        print(f"Error: {str(e)}")