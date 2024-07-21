from selenium import webdriver # type: ignore
from selenium.webdriver.chrome.service import Service # type: ignore
from selenium.webdriver.chrome.options import Options # type: ignore
from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from database.db import SessionLocal
from database.models import JobListing
import logging

def scrape_apple_jobs():
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
        current_job_ids = {job.job_id for job in session.query(JobListing.job_id).all()}

        base_url = 'https://jobs.apple.com/en-us/search?location=united-states-USA&team=internships-STDNT-INTRN'
        driver.get(base_url)
        links = driver.find_elements(By.CLASS_NAME, "table--advanced-search__title")
        links[:] = [link.get_attribute('href') for link in links]

        wait = WebDriverWait(driver, 10)
        new_job_ids = set()

        for link in links:
            try:
                driver.get(link)
                
                job_id = link.split('/')[5]
                new_job_ids.add(job_id)
                
                # Check if the job exists
                title_element = driver.find_elements(By.ID, "jdPostingTitle")
                if not title_element:
                    continue
                
                title = title_element[0].text
                description = wait.until(EC.presence_of_element_located((By.ID, "jd-description"))).text
                min_q_div = wait.until(EC.presence_of_element_located((By.ID, "jd-minimum-qualifications")))
                min_qualifications = [m.text for m in min_q_div.find_elements(By.TAG_NAME, "li")]
                pref_q_div = wait.until(EC.presence_of_element_located((By.ID, "jd-preferred-qualifications")))
                pref_qualifications = [p.text for p in pref_q_div.find_elements(By.TAG_NAME, "li")]
                qualifications = min_qualifications + pref_qualifications
                locations = [wait.until(EC.presence_of_element_located((By.ID, "job-location-name"))).text]
                miscellaneous = wait.until(EC.presence_of_element_located((By.ID, "jd-job-summary"))).text

                # Check if the job listing already exists
                existing_listing = session.query(JobListing).filter_by(job_id=job_id).first()
                
                if existing_listing:
                    # Update the existing job listing
                    existing_listing.job_link = link
                    existing_listing.title = title
                    existing_listing.company = "Apple"
                    existing_listing.category = None
                    existing_listing.description = description
                    existing_listing.qualifications = qualifications
                    existing_listing.locations = locations
                    existing_listing.miscellaneous = miscellaneous
                    existing_listing.responsibilities = None
                    logger.info(f"Updated job listing: {job_id}")
                else:
                    # Insert a new job listing
                    job_listing = JobListing(
                        job_link=link,
                        job_id=job_id,
                        title=title,
                        company="Apple",
                        category=None,
                        description=description,
                        qualifications=qualifications,
                        locations=locations,
                        miscellaneous=miscellaneous,
                        responsibilities=None
                    )
                    session.add(job_listing)
                    logger.info(f"Added new job listing: {job_id}")

                session.commit()

            except Exception as e:
                logger.error(f"Failed to process {link}: {e}")

        # Find job IDs that are no longer present on the website and delete them
        job_ids_to_delete = current_job_ids - new_job_ids
        for job_id in job_ids_to_delete:
            job_to_delete = session.query(JobListing).filter_by(job_id=job_id).first()
            if job_to_delete:
                session.delete(job_to_delete)
                session.commit()
                logger.info(f"Deleted job listing: {job_id}")

    finally:
        driver.quit()
        session.close()
