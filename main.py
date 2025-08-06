import json
import logging
import time
from datetime import datetime

import pandas as pd

from scraper import load_config, scrape_tenders, is_tender_relevant

def main():
    """
    Main function to run the tender scraping and filtering process.
    """
    # --- Setup ---
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    start_time = time.time()
    logging.info("--- Starting the Government Tender Monitoring Script ---")

    # --- Load Configuration ---
    config = load_config()
    if not config:
        logging.error("Exiting due to missing or invalid configuration.")
        return

    # --- Step 1: Scrape Raw Data ---
    logging.info("[Step 1: Scraping raw data]")
    raw_tenders_list = scrape_tenders(config.get("scraper_config", {}))
    if not raw_tenders_list:
        logging.warning("Scraping did not return any data. The website might be down or has changed.")
    else:
        logging.info(f"Successfully downloaded {len(raw_tenders_list)} raw tenders.")

    # --- Step 2: Filter Tenders ---
    logging.info("\n[Step 2: Applying filtering logic]")
    filtered_tenders_list = []
    if raw_tenders_list:
        filter_rules = config.get("filter_rules", {})
        for tender in raw_tenders_list:
            if is_tender_relevant(tender.get('標案名稱', ''), filter_rules):
                filtered_tenders_list.append(tender)
    logging.info(f"Filtering complete. Found {len(filtered_tenders_list)} relevant tenders.")

    # --- Step 3: Format and Save Results ---
    logging.info("\n[Step 3: Formatting and saving results]")
    if filtered_tenders_list:
        today_str = datetime.today().strftime('%Y-%m-%d')

        # Save JSON cache file
        try:
            cache_filename = f"daily_cache_{today_str}.json"
            daily_cache_map = {tender['標案案號']: tender for tender in filtered_tenders_list}
            with open(cache_filename, 'w', encoding='utf-8') as f:
                json.dump(daily_cache_map, f, ensure_ascii=False, indent=4)
            logging.info(f"Results saved to JSON cache file: {cache_filename}")
        except IOError as e:
            logging.error(f"Failed to save JSON cache file: {e}")

        # Save CSV file
        try:
            df = pd.DataFrame(filtered_tenders_list)
            # Reorder columns for better readability, as in the original script
            display_columns = [
                "公告日期", "截止投標", "機關名稱", "標案名稱",
                "預算金額", "招標方式", "標案案號", "標案連結"
            ]
            # Ensure all display columns exist in the DataFrame, add if missing
            for col in display_columns:
                if col not in df.columns:
                    df[col] = "N/A"

            df_display = df[display_columns]
            csv_filename = f"filtered_tenders_{today_str}.csv"
            df_display.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            logging.info(f"Results saved to CSV file: {csv_filename}")
        except (IOError, KeyError) as e:
            logging.error(f"Failed to save CSV file: {e}")

    else:
        logging.info("No relevant tenders found today that match the filter criteria.")

    # --- Wrap up ---
    end_time = time.time()
    logging.info(f"\n--- Script finished in {end_time - start_time:.2f} seconds ---")


if __name__ == "__main__":
    main()
