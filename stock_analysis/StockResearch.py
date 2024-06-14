import requests
from bs4 import BeautifulSoup
import pandas as pd
import ftplib
import os
import sys
import random
from colorama import Fore, Style
from selenium import webdriver
import pkg_resources

class StockResearch:
    def __init__(self, debug=False):
        self.debug = debug
        if self.debug:
            print("StockResearch::StockResearch --> Grabbing All Tickers...")
        self.filenames = ["nasdaqlisted.txt", "otherlisted.txt"]

    def fetch_csv_data(self, url):
        response = requests.get(url)
        response.raise_for_status()
        return response.text

    def get_ticker_symbols(self):
        # Check if we already have the files
        count = 0
        for filename in self.filenames:
            filepath = pkg_resources.resource_filename('StockApp.data', filename)
            if os.path.exists(filepath):
                if self.debug:
                    print("StockResearch::get_ticker_symbols File -->", filename, " found.")
                count += 1

        if count == 2:
            if self.debug:
                print("StockResearch::get_ticker_symbols --> Skipping Download...")
        else:
            ftp_server = ftplib.FTP("ftp.nasdaqtrader.com")
            ftp_server.login()
            ftp_server.encoding = "utf-8"
            ftp_server.cwd('Symboldirectory')
            ftp_server.dir()

            for filename in self.filenames:
                with open(filename, "wb") as file:
                    ftp_server.retrbinary(f"RETR {filename}", file.write)
            ftp_server.quit()

    def list_ticker_symbols(self):
        df = pd.read_csv("nasdaqlisted.txt", sep="|")
        df2 = pd.read_csv("otherlisted.txt", sep="|")
        # filter out ETFs
        filtered_df1 = df[df['ETF'] != "Y"]
        filtered_df2 = df2[df2['ETF'] != "Y"]
        # Combine into one dataframe
        combined_df = pd.concat([filtered_df1, filtered_df2], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['Symbol'])
        if self.debug:
            print(combined_df.head(10))
            print("StockResearch::list_ticker_symbols Total Tickers: ", len(combined_df))
        tickers = combined_df['Symbol'].to_list()
        filtered_tickers = [value for value in tickers if isinstance(value, str) and not value.startswith("File")]
        return filtered_tickers

    def compare_files(self, file1, file2):
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()

        # Find lines that are in file1 but not in file2
        lines_unique_to_file1 = [line.strip() for line in lines1 if line.strip() not in lines2]

        # Find lines that are in file2 but not in file1
        lines_unique_to_file2 = [line.strip() for line in lines2 if line.strip() not in lines1]

        return lines_unique_to_file1, lines_unique_to_file2

    def choose_tickers(self, my_list, number):
        random_tickers = random.sample(my_list, number)
        if self.debug:
            print("StockResearch::choose_tickers Tickers Chosen --> ", random_tickers)
        return random_tickers

    def grab_dogs_of_the_dow(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(options=options)

        # Send a GET request to the Dogs of the Dow website
        url = 'https://www.dogsofthedow.com/dogday.htm'
        driver.get(url)
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # if self.debug:
        #     print("StockResearch::grab_dogs_of_the_dow --> Soup: ", soup)
        # Find the table containing the tickers
        table = soup.find('table', class_='tablepress tablepress-id-5 tablepress-responsive dataTable no-footer')
        # Extract tickers from the table
        tickers = []
        if table:
            for row in table.find_all('tr')[1:]:  # Skip header row
                ticker = row.find_all('td')[0].text.strip()
                tickers.append(ticker)
            if self.debug:
                # Print the extracted tickers
                print("StockResearch::grab_dogs_of_the_dow --> " \
                "Tickers from Dogs of the Dow:")
                for ticker in tickers:
                    print(ticker)

        else:
            print(Fore.RED + "FATAL ERROR StockResearch::grab_dogs_of_the_dow " \
            "--> Failed to find Table of tickers." + Style.RESET_ALL)

        driver.quit()
        return soup

    def find_and_print_soup_content(self, soup, target_word, content_amount=1000):
        # Find all text elements in the soup
        text_elements = soup.find_all(text=True)

        # Join all text elements into a single string
        full_text = ' '.join(text_elements)

        # Find the index of the target word in the full text
        word_index = full_text.find(target_word)

        if word_index != -1:
            # Extract 100 words before and after the target word
            context_start = max(0, word_index - content_amount)
            context_end = min(len(full_text), word_index + len(target_word) + content_amount)
            context = full_text[context_start:context_end]
            # Print the context
            print("Context around '{}':".format(target_word))
            print(context)
        else:
            print("Word '{}' not found in the text.".format(target_word))

    def find_elements_by_keyword(self, soup, keyword):
        # Find all elements containing the keyword in their text or attributes
        elements = soup.find_all(lambda tag: keyword in tag.text or keyword in tag.get('class', []))
        #elements = soup.find_all(lambda tag: tag.name if tag.name else '').find_all(text=lambda text: keyword in text or keyword in tag.get('class', []))
        # Print the found elements
        if self.debug:
            for element in elements:
                print(element)
        return elements

    # Example usage:
    # Assuming 'soup' is the BeautifulSoup object and 'keyword' is the keyword to search for
    # Replace 'soup' and 'keyword' with your specific values

    # Find elements containing the keyword
    #found_elements = find_elements_by_keyword(soup, 'Symbol')
