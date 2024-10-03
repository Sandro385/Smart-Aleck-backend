from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def open_webpage(url):
    # Set up Chrome options
    options = Options()
    
    # Create a new instance of the Chrome driver
    service = Service('/usr/local/bin/chromedriver')  # Replace with the path to your ChromeDriver
    driver = webdriver.Chrome(service=service, options=options)
    
    # Open the webpage
    driver.get(url)
    
    return driver

def click_fourth_link(driver):
    try:
        # Use a CSS selector to find all <a> elements within the specified structure
        links = driver.find_elements(By.CSS_SELECTOR, "div.panel-heading p a")
        
        # Check if there are more than 3 elements to ignore
        if len(links) > 3:
            # Click the fourth link (index 3)
            links[3].click()
            print(f"Clicked on the fourth link: {links[3].text}")
        else:
            print(f"Not enough links found: {len(links)}")
    except Exception as e:
        print(f"Error: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Open the webpage
    driver = open_webpage("https://matsne.gov.ge/en/document/search?page=1")  # Replace with your target URL
    
    # Wait for the page to load
    time.sleep(5)  # Adjust the sleep time as necessary

    # Click on the fourth link in the panel heading
    click_fourth_link(driver)
    
    # Close the driver
    driver.quit()