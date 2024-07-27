from selenium import webdriver # type: ignore
from selenium.webdriver.chrome.service import Service # type: ignore
from selenium.webdriver.chrome.options import Options # type: ignore
from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from database.db import SessionLocal
from database.models import JobListing
import logging

def scrape_microsoft_jobs():
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

    # Create a new session
    session = SessionLocal()

    try:
        # Fetch all current job IDs from the database
        current_job_ids = {job.job_id for job in session.query(JobListing.job_id).filter_by(company="Microsoft").all()}

        base_url = 'https://jobs.careers.microsoft.com/global/en/search?lc=United%20States&exp=Students%20and%20graduates'
        driver.get(base_url)
        wait = WebDriverWait(driver, 20)
        links = []
        new_job_ids = set()

        try:
            # Wait for the page to load completely
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-automationid='ListCell']")))

            # Extract job listing elements
            elements = driver.find_elements(By.CSS_SELECTOR, "[data-automationid='ListCell']")

            for index in range(len(elements)):
                try:
                    # Re-fetch the elements to ensure we get a fresh list each time
                    elements = driver.find_elements(By.CSS_SELECTOR, "[data-automationid='ListCell']")
                    element = elements[index]

                    btn = element.find_element(By.TAG_NAME, "button")
                    btn.click()

                    # Wait for the URL to change or new page to load after clicking the button
                    WebDriverWait(driver, 10).until(lambda d: d.current_url != base_url)
                    job_link = driver.current_url
                    links.append(job_link)

                    # Navigate back to the main job search page
                    driver.get(base_url)

                    # Wait for the page to load again
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-automationid='ListCell']")))
                except Exception as inner_e:
                    logger.error(f"An error occurred while processing an element: {inner_e}")
                    continue
        except Exception as e:
            logger.error(f"An error occurred: {e}")

        for link in links:
            driver.get(link)

            try:
                title_el = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'h1')))
                title = title_el.text
                
                id_div = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-search-app"]/div/div[2]/div/div/div/div[4]/div[2]/div/div[2]')))
                job_id = id_div.text
                new_job_ids.add(job_id)
                
                desc_div = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-search-app"]/div/div[2]/div/div/div/div[5]/div[1]/div/div')))
                description = desc_div.text
                
                qual_div = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-search-app"]/div/div[2]/div/div/div/div[5]/div[2]/div/div')))
                quals = qual_div.find_elements(By.TAG_NAME, 'li')
                qualifications = [q.text for q in quals]
                
                loc_p = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-search-app"]/div/div[2]/div/div/div/div[2]/div/p')))
                locations = [loc_p.text]
                
                resp_div = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-search-app"]/div/div[2]/div/div/div/div[5]/div[3]/div/div')))
                resps = resp_div.find_elements(By.TAG_NAME, 'li')
                responsibilities = [r.text for r in resps]
                
                category_div = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-search-app"]/div/div[2]/div/div/div/div[4]/div[7]/div/div[2]')))
                category = category_div.text

                # Check if the job listing already exists
                existing_listing = session.query(JobListing).filter_by(job_id=job_id, company="Microsoft").first()

                if existing_listing:
                    # Update the existing job listing
                    existing_listing.job_link = link
                    existing_listing.title = title
                    existing_listing.company = "Microsoft"
                    existing_listing.category = category
                    existing_listing.description = description
                    existing_listing.qualifications = qualifications
                    existing_listing.locations = locations
                    existing_listing.miscellaneous = None
                    existing_listing.responsibilities = responsibilities
                    logger.info(f"Updated job listing: {job_id}")
                else:
                    # Insert a new job listing
                    job_listing = JobListing(
                        job_link=link,
                        job_id=job_id,
                        title=title,
                        company="Microsoft",
                        category=category,
                        description=description,
                        qualifications=qualifications,
                        locations=locations,
                        miscellaneous=None,
                        responsibilities=responsibilities
                    )
                    session.add(job_listing)
                    logger.info(f"Added new job listing: {job_id}")

                session.commit()

            except Exception as e:
                logger.error(f"An error occurred while trying to retrieve the job ID from {link}: {e}")

        # Find job IDs that are no longer present on the website and delete them
        job_ids_to_delete = current_job_ids - new_job_ids
        for job_id in job_ids_to_delete:
            job_to_delete = session.query(JobListing).filter_by(job_id=job_id, company="Microsoft").first()
            if job_to_delete:
                session.delete(job_to_delete)
                session.commit()
                logger.info(f"Deleted job listing: {job_id}")
    finally:
        driver.quit()
        session.close()
