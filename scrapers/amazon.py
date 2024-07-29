from selenium import webdriver # type: ignore
from selenium.webdriver.chrome.service import Service # type: ignore
from selenium.webdriver.chrome.options import Options # type: ignore
from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from database.db import SessionLocal
from database.models import JobListing
import logging

def scrape_amazon_jobs():
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
        current_job_ids = {job.job_id for job in session.query(JobListing.job_id).filter_by(company="Amazon").all()}

        base_url = 'https://amazon.jobs/content/en/career-programs/university?country%5B%5D=US'
        driver.get(base_url)
        wait = WebDriverWait(driver, 20)
        links = []
        new_job_ids = set()

        try:
            job_listings = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'header-module_title__9-W3R')))
            for job in job_listings:
                link = job.get_attribute('href')
                if link: links.append(link)
        except Exception as links_e:
            logger.info(f"An error occurred: {links_e}")

        for link in links:
            driver.get(link)
            
            try:
                id_sec = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-detail"]/div[1]/div/div/div/div[1]/div/div/p')))
                id_txt = id_sec.text
                id_arr = id_txt.split()
                job_id = id_arr[2]
                new_job_ids.add(job_id)
                
                title = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'h1'))).text
                
                category = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-detail-body"]/div/div[2]/div/div[1]/ul/li[3]/div/ul'))).text
                
                description = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-detail-body"]/div/div[1]/div/div[2]/p'))).text
                
                loc_lst = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-detail-body"]/div/div[2]/div/div[1]/ul/li[1]/div/ul')))
                locations = loc_lst.find_elements(By.TAG_NAME, 'li')
                
                basic_reqs = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-detail-body"]/div/div[1]/div/div[3]/p'))).text
                basic = [line.strip()[2:] for line in basic_reqs.splitlines() if line.strip()]
                pref_reqs = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="job-detail-body"]/div/div[1]/div/div[4]/p'))).text
                lines = pref_reqs.splitlines()
                identifiers = ['- ', '* ', '• ']
                last_requirement_index = -1
                for i, line in enumerate(lines):
                    if any(line.strip().startswith(identifier) for identifier in identifiers):
                        last_requirement_index = i
                preferred = [line.strip()[2:] for line in lines[:last_requirement_index + 1] if any(line.strip().startswith(identifier) for identifier in identifiers)]
                qualifications = basic + preferred
                
                miscellaneous = "\n".join(lines[last_requirement_index + 1:]).strip()

                # Check if the job listing already exists
                existing_listing = session.query(JobListing).filter_by(job_id=job_id, company="Amazon").first()

                if existing_listing:
                    # Update the existing job listing
                    existing_listing.job_link = link
                    existing_listing.title = title
                    existing_listing.company = "Amazon"
                    existing_listing.category = category
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
                        company="Amazon",
                        category=category,
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
                logger.info(f"An error occurred: {e}")
        
        # Find job IDs that are no longer present on the website and delete them
        job_ids_to_delete = current_job_ids - new_job_ids
        for job_id in job_ids_to_delete:
            job_to_delete = session.query(JobListing).filter_by(job_id=job_id, company="Amazon").first()
            if job_to_delete:
                session.delete(job_to_delete)
                session.commit()
                logger.info(f"Deleted job listing: {job_id}")
    finally:
        driver.quit()
        session.close()
