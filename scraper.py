import json
import logging
import time
import random
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# --- Configuration ---
def load_config(config_path="config.json"):
    """Loads the configuration file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Configuration file not found at: {config_path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from the configuration file: {config_path}")
        return None

# --- Filtering Logic ---
def is_tender_relevant(tender_name, filter_rules):
    """
    Applies the 3-tier filtering logic to a tender name.
    """
    if not tender_name or not filter_rules:
        return False

    tender_name_lower = tender_name.lower()

    # Tier 1: Global Absolute Rejection
    for reject_word in filter_rules.get("level_1_absolute_reject_keywords", []):
        if reject_word.lower() in tender_name_lower:
            return False

    # Tier 2 & 3: Contextual Matching & Loose Inclusion
    has_valid_match = False
    for rule in filter_rules.get("level_2_contextual_rules", []):
        keyword_lower = rule["keyword"].lower()
        if keyword_lower in tender_name_lower:
            is_contaminated = False
            for reject_word in rule["adjacent_rejects"]:
                if f"{keyword_lower}{reject_word.lower()}" in tender_name_lower or \
                   f"{reject_word.lower()}{keyword_lower}" in tender_name_lower:
                    is_contaminated = True
                    break

            if not is_contaminated:
                has_valid_match = True
                break

    return has_valid_match

# --- Scraping and Parsing Logic ---
def scrape_tenders(scraper_config):
    """
    Scrapes tender information by first visiting the page to get cookies,
    then posting the search form.
    """
    logging.info("Starting to scrape tenders with 2-step requests approach...")

    session = requests.Session()
    session.headers.update(scraper_config.get("headers", {}))
    # The POST endpoint from the spec
    target_url = "https://web.pcc.gov.tw/tps/pss/tender.do?searchMode=common&searchType=basic"

    try:
        # Step 1: Visit the page to get initial cookies
        logging.info(f"Step 1: Making a GET request to {target_url} to establish session.")
        session.get(target_url, timeout=20)
        logging.info("Session established, cookies should be set.")

        time.sleep(random.uniform(1.5, 3.5))

        # Step 2: Post the form with the acquired session cookies
        today = datetime.today()
        minguo_year = today.year - 1911
        date_str = f"{minguo_year}/{today.month:02d}/{today.day:02d}"

        form_data = {
            "method": "search", "searchMethod": "true", "tenderName": "", "tenderId": "",
            "tenderType": "tenderDeclaration", "tenderWay": "1,2,3,4,5,6,7,10,12",
            "tenderDateRadio": "on", "tenderStartDate": date_str, "tenderEndDate": date_str,
            "tenderStatus": "5,6,20,28", "radProctrgCate": "", "proctrgCate": "",
            "location": "", "tenderOrg": "", "tenderOrgId": "", "isSpdt": "",
            "d-1484221-p": "1", "pageSize": "1000"
        }

        logging.info(f"Step 2: Posting to {target_url} with date {date_str}")
        response = session.post(target_url, data=form_data, timeout=30)
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP Request failed: {e}")
        return []

    logging.info(f"Response received with status code: {response.status_code}")

    # --- HTML Parsing ---
    # The selector for the table on the POST result page
    table_selector = "table#list_list_content_table"
    soup = BeautifulSoup(response.text, 'lxml')

    table = soup.select_one(table_selector)
    if not table:
        logging.warning("Could not find the results table on the page.")
        debug_path = Path("debug_page.html")
        debug_path.write_text(response.text, encoding='utf-8')
        logging.warning(f"Saved page content to {debug_path} for debugging. This is expected if the IP is blocked.")
        return []

    raw_tenders = []
    rows = table.select("tr:not(.list_head)")
    logging.info(f"Found {len(rows)} tender rows in the table.")

    for row in rows:
        try:
            link_tag = row.select_one("td:nth-of-type(3) a")
            if not link_tag: continue

            name_cell_text = row.select_one("td:nth-of-type(3)").text.strip()
            case_no_text = link_tag.text.strip()
            tender_name = name_cell_text.replace(case_no_text, '').strip()

            tender_data = {
                "機關名稱": row.select_one("td:nth-of-type(2)").text.strip(),
                "標案案號": case_no_text,
                "標案名稱": tender_name,
                "傳輸次數": row.select_one("td:nth-of-type(4)").text.strip(),
                "招標方式": row.select_one("td:nth-of-type(5)").text.strip(),
                "採購性質": row.select_one("td:nth-of-type(6)").text.strip(),
                "公告日期": row.select_one("td:nth-of-type(7)").text.strip(),
                "截止投標": row.select_one("td:nth-of-type(8)").text.strip(),
                "預算金額": row.select_one("td:nth-of-type(9)").text.strip().replace(',', ''),
                "標案連結": "https://web.pcc.gov.tw" + link_tag['href']
            }
            raw_tenders.append(tender_data)
        except (AttributeError, TypeError) as e:
            logging.warning(f"Could not parse a row, skipping. Error: {e}. Row: {row.text.strip()}")
            continue

    logging.info(f"Successfully parsed {len(raw_tenders)} tenders.")
    return raw_tenders
