from selenium import webdriver # type: ignore
from selenium.webdriver.chrome.service import Service # type: ignore
from selenium.webdriver.chrome.options import Options # type: ignore
from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from database.db import SessionLocal
from database.models import JobListing
import logging
import time

def scrape_tesla_jobs():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # Initialize the Chrome driver with the options
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    # Create a new session
    session = SessionLocal()

    try:
        # Fetch all current job IDs from the database
        current_job_ids = {job.job_id for job in session.query(JobListing.job_id).filter_by(company="Tesla").all()}

        urls = [
            'https://www.tesla.com/careers/search/?type=3&site=US&department=ai-robotics',
            'https://www.tesla.com/careers/search/?type=3&site=US&department=charging',
            'https://www.tesla.com/careers/search/?type=3&site=US&department=energy-solar-storage',
            'https://www.tesla.com/careers/search/?type=3&site=US&department=engineering-information-technology',
            'https://www.tesla.com/careers/search/?type=3&site=US&department=finance',
            'https://www.tesla.com/careers/search/?type=3&site=US&department=supply-chain',
            'https://www.tesla.com/careers/search/?type=3&site=US&department=vehicle-software'
        ]
        links = []
        new_job_ids = set()

        def scrape_page(url):
            driver.get(url)
            last_height = driver.execute_script("return document.body.scrollHeight")

            while True:
                try:
                    # Collect job postings on the current page
                    job_postings = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "tds-link")))
                    job_links = [j.get_attribute('href') for j in job_postings]

                    # Add new links to the list
                    links.extend(job_links)

                    # Scroll down to the bottom of the page
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)  # Wait for new content to load

                    # Check if we've reached the bottom of the page
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                except Exception as e:
                    logger.error(f"An error occurred while scraping {url}: {e}")
                    break

        # Iterate over all URLs and scrape them
        for url in urls:
            scrape_page(url)

        # Remove duplicates and unwanted links
        links = list(set(links))
        links = [link for link in links if link not in ["https://www.tesla.com/about", "https://www.tesla.com/about/legal", "https://inside.tesla.com/"]]

        for link in links:
            driver.get(link)
            
            try:
                # Wait for elements to be present and visible
                job_id = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[2]/table/tbody/tr[3]/td'))).text
                
                title = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/h1'))).text
                
                category = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[2]/table/tbody/tr[1]/td'))).text
                
                try:
                    description = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[4]/div[1]/p'))).text
                except:
                    description = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[4]/div[1]'))).text
                
                location = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[2]/table/tbody/tr[2]/td'))).text
                locations = [location]
                
                try:
                    qual_lst = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[4]/div[3]/ul')))
                except:
                    qual_lst = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[4]/div[3]/div/ul')))
                quals = qual_lst.find_elements(By.TAG_NAME, 'li')
                qualifications = [q.text for q in quals]
                
                try:
                    resp_lst = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[4]/div[2]/ul')))
                except:
                    resp_lst = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[4]/div[3]/div/ul')))
                resps = resp_lst.find_elements(By.TAG_NAME, 'li')
                responsibilities = [r.text for r in resps]
                
                try:
                    misc = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[5]/div/div[4]/p'))).text
                    miscellaneous = misc.splitlines()[0]
                except:
                    miscellaneous = None

                # Check if the job listing already exists
                existing_listing = session.query(JobListing).filter_by(job_id=job_id, company="Tesla").first()

                if existing_listing:
                    # Update the existing job listing
                    existing_listing.job_link = link
                    existing_listing.title = title
                    existing_listing.company = "Tesla"
                    existing_listing.category = category
                    existing_listing.description = description
                    existing_listing.qualifications = qualifications
                    existing_listing.locations = locations
                    existing_listing.miscellaneous = miscellaneous
                    existing_listing.responsibilities = responsibilities
                    logger.info(f"Updated job listing: {job_id}")
                else:
                    # Insert a new job listing
                    job_listing = JobListing(
                        job_link=link,
                        job_id=job_id,
                        title=title,
                        company="Tesla",
                        category=category,
                        description=description,
                        qualifications=qualifications,
                        locations=locations,
                        miscellaneous=miscellaneous,
                        responsibilities=responsibilities
                    )
                    session.add(job_listing)
                    logger.info(f"Added new job listing: {job_id}")

                session.commit()
            except Exception as e:
                logger.error(f"An error occurred: {e}")
        
        # Find job IDs that are no longer present on the website and delete them
        job_ids_to_delete = current_job_ids - new_job_ids
        for job_id in job_ids_to_delete:
            job_to_delete = session.query(JobListing).filter_by(job_id=job_id, company="Tesla").first()
            if job_to_delete:
                session.delete(job_to_delete)
                session.commit()
                logger.info(f"Deleted job listing: {job_id}")
    finally:
        driver.quit()
        session.close()
