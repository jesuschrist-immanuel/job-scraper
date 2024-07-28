from selenium import webdriver # type: ignore
from selenium.webdriver.chrome.service import Service # type: ignore
from selenium.webdriver.chrome.options import Options # type: ignore
from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from database.db import SessionLocal
from database.models import JobListing
import logging

def scrape_google_jobs():
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
        current_job_ids = {job.job_id for job in session.query(JobListing.job_id).filter_by(company="Google").all()}

        base_url = 'https://www.google.com/about/careers/applications/jobs/results/?employment_type=INTERN&location=United%20States'
        driver.get(base_url)
        wait = WebDriverWait(driver, 20)
        links = []
        new_job_ids = set()

        try:
            job_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[jsname="hSRGPd"]')))
            for job in job_elements:
                link = job.get_attribute('href')
                if link: links.append(link)
        except Exception as links_e:
            logger.error(f"An error occurred: {links_e}")
        
        for link in links:
            driver.get(link)
            
            parts = link.split('/')
            job_id_part = parts[-1]
            job_id = job_id_part.split('-')[0]
            new_job_ids.add(job_id)
            
            try:
                title = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'p1N2lc'))).text
                
                desc_div = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'aG5W3')))
                desc_ps = desc_div.find_elements(By.TAG_NAME, 'p')
                desc_ps[:] = [e.text for e in desc_ps]
                description = " ".join(desc_ps)
                
                locations_string = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'b'))).text
                locations = [loc.strip() for loc in locations_string.split(';') if loc.strip()]
                
                min_qual_lst = wait.until(EC.presence_of_element_located((By.XPATH, '//h3[contains(text(), "Minimum qualifications:")]/following-sibling::ul[1]')))
                min_quals = min_qual_lst.find_elements(By.TAG_NAME, "li")
                min_qualifications = [q.text for q in min_quals]
                pref_qual_lst = wait.until(EC.presence_of_element_located((By.XPATH, '//h3[contains(text(), "Preferred qualifications:")]/following-sibling::ul[1]')))
                pref_quals = pref_qual_lst.find_elements(By.TAG_NAME, "li")
                pref_qualifications = [q.text for q in pref_quals]
                qualifications = min_qualifications + pref_qualifications
                
                resp_div = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'BDNOWe')))
                resps = resp_div.find_elements(By.TAG_NAME, 'li')
                responsibilities = [r.text for r in resps]

                misc_sec = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'MyVLbf')))
                misc_ps = misc_sec.find_elements(By.TAG_NAME, 'p')
                misc_ps[:] = [e.text for e in misc_ps]
                miscellaneous = " ".join(misc_ps)

                # Check if the job listing already exists
                existing_listing = session.query(JobListing).filter_by(job_id=job_id, company="Google").first()

                if existing_listing:
                    # Update the existing job listing
                    existing_listing.job_link = link
                    existing_listing.title = title
                    existing_listing.company = "Google"
                    existing_listing.category = None
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
                        company="Google",
                        category=None,
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
            job_to_delete = session.query(JobListing).filter_by(job_id=job_id, company="Google").first()
            if job_to_delete:
                session.delete(job_to_delete)
                session.commit()
                logger.info(f"Deleted job listing: {job_id}")
    finally:
        driver.quit()
        session.close()
