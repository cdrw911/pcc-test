# Government Tender Scraper

This project contains a Python script to scrape tender announcements from Taiwan's government procurement website (`web.pcc.gov.tw`).

It is designed to be run from a server with a "clean" IP address to avoid being blocked by the website's WAF.

## Setup

1.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The `config.json` file contains all the necessary configurations for the scraper.

-   `scraper_config`: Contains the target URL, request headers, and CSS selectors for parsing the data.
-   `filter_rules`: Contains the keywords for filtering the tenders.
    -   `level_1_absolute_reject_keywords`: Tenders containing these keywords will be excluded.
    -   `level_2_contextual_rules`: Tenders are matched based on a keyword, but excluded if a `adjacent_reject` word is also present.

You can modify this file to change the scraping and filtering behavior without changing the code.

## Usage

To run the scraper, execute the `main.py` script:

```bash
python main.py
```

The script will:
1.  Fetch the latest tender announcements for the current day.
2.  Filter them according to the rules in `config.json`.
3.  Save the filtered results to `filtered_tenders_YYYY-MM-DD.csv`.
4.  Save a JSON cache of the day's results to `daily_cache_YYYY-MM-DD.json`.

Logs will be printed to the console.
