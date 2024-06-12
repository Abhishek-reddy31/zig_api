from flask import Flask, request, render_template
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
import time
import re

CHROME_DRIVER_PATH = 'chromedriver.exe'

app = Flask(__name__)

# Global data store
data_store = {
    'formart': pd.DataFrame(),
    'zigguratss': pd.DataFrame(),
    'artflute': pd.DataFrame(),
    'fizdi': pd.DataFrame(),
    'mojarto': pd.DataFrame(),
    'saatchiart': pd.DataFrame(),
    'combined': pd.DataFrame()
}

def clean_price(price):
    # Remove any non-numeric characters except the decimal point and currency symbol
    price = re.sub(r'[^\d.₹]', '', price)
    return price

def clean_artist_name(name):
    if name.startswith('Piture Art by'):
        return name.replace('Piture Art by', '').strip()
    return name.strip()

def clean_artist_name2(name):
    if name.startswith('By'):
        return name.replace('By', '').strip()
    return name.strip()

def scrape_formart():
    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service)
    url = 'https://theformart.com/entire-collection/by-artworks.html'
    driver.get(url)

    for _ in range(100):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
        time.sleep(1)
        driver.find_element('tag name', 'body').send_keys(Keys.PAGE_UP)
        time.sleep(0.5)

    page_content = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page_content, 'lxml')
    products = soup.find_all('div', class_='product-item-info')

    names, prices, artists = [], [], []
    for product in products:
        name_tag = product.find('strong', class_='product name product-item-name')
        price_tag = product.find('span', class_='price')
        artist_tag = product.find('div', class_='artist-name-plp')

        names.append(name_tag.text.strip() if name_tag else 'Unknown')
        prices.append(clean_price(price_tag.text.strip() if price_tag else 'Unknown'))
        artists.append(artist_tag.text.strip() if artist_tag else 'Unknown')

    return pd.DataFrame({'Name': names, 'Price': prices, 'Artist': artists, 'Website': 'Formart'})

def scrape_zigguratss():
    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service)
    url = 'https://zigguratss.com/allwork/'
    driver.get(url)
    time.sleep(5)

    total_paintings_scraped = 0
    while True:
        try:
            see_more_button = driver.find_element('class name', 'see_more_btn')
            see_more_button.click()
            time.sleep(2)
            total_paintings_scraped += 16
        except:
            break

    page_content = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page_content, 'lxml')
    names_tags = soup.find_all('div', class_='artwork-name')
    prices_tags = soup.find_all('div', class_='artwork-price')
    artists_tags = soup.find_all('a', class_='artwork-artist artwork_name')

    names = [name.a.text.strip() for name in names_tags]
    prices = [clean_price(price.text.strip()) for price in prices_tags]
    artists = [artist.text.strip() for artist in artists_tags]

    return pd.DataFrame({'Name': names, 'Price': prices, 'Artist': artists, 'Website': 'Zigguratss'})

def scrape_artflute():
    artflute_df = pd.DataFrame(columns=['Name', 'Price', 'Artist'])
    no = 1
    for i in range(0, 185):
        url = 'https://www.artflute.com/artworks/all?page=' + str(no)
        no += 1
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            page_content = response.content
            soup = BeautifulSoup(page_content, 'lxml')
            names_tags = soup.find_all('h2', class_='artwork-name')
            prices_tags = soup.find_all('span', class_='money')
            artists_tags = soup.find_all('p', class_='artist-name')
            names = [name.a.text.strip() for name in names_tags]
            prices = [clean_price('₹' + price.text.strip() if price is not None else '') for price in prices_tags]
            artists = [artist.a.text.strip() if artist is not None else '' for artist in artists_tags]
            data = [{'Name': name, 'Price': price, 'Artist': artist} for name, price, artist in zip(names, prices, artists)]
            new_artflute_df = pd.DataFrame(data)
            artflute_df = pd.concat([artflute_df, new_artflute_df], ignore_index=True)
        except requests.HTTPError as e:
            print(f"HTTP error occurred for page {no - 1}: {e}")
        except requests.RequestException as e:
            print(f"An error occurred for page {no - 1}: {e}")
        time.sleep(0.3)
    return artflute_df

def scrape_fizdi():
    all_data = []
    for page_no in range(0, 436):
        url = f'https://www.fizdi.com/paintings-online/?mode=6&limit=100&page={page_no}'
        response = requests.get(url)
        page_content = response.content
        soup = BeautifulSoup(page_content, 'lxml')
        names = soup.find_all('h3', class_='card-title')
        prices = soup.find_all('span', class_='price price--withTax price--main _hasSale')
        artist_names = soup.find_all('div', class_='card-text card-text--brand')
        artist_names = [artist.find('a').text.strip() for artist in artist_names if artist.find('a')]
        data = [{'Name': name.text.strip(), 'Price': clean_price(price.text.strip()), "Artist": artist_name} for name, price, artist_name in zip(names, prices, artist_names)]
        all_data.extend(data)
    fizdi_df = pd.DataFrame(all_data)
    return fizdi_df

def scrape_mojarto():
    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service)
    base_url = 'https://www.mojarto.com/artworks?sort=Newest&pageNumber={}'
    all_data = []
    for page_num in range(333):
        try:
            url = base_url.format(page_num)
            driver.get(url)
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            artworks = soup.find_all('div', class_='product-list-content')
            for artwork in artworks:
                name = artwork.find('h3', class_='product-title').text.strip()
                artist = artwork.find('a', class_='product-author').text.strip().replace('By ', '')
                price = artwork.find('span', class_='product-amount').text.strip().replace('₹', '').replace(',', '')
                all_data.append({'Name': name, 'Price': clean_price('₹ ' + price), 'Artist': artist})
        except Exception as e:
            print(f"An error occurred while scraping page {page_num}: {e}")
    driver.quit()
    mojarto_df = pd.DataFrame(all_data)
    return mojarto_df

def scrape_saatchiart():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    all_data = []
    for page_num in range(1, 501):
        url = f'https://www.saatchiart.com/paintings?page={page_num}'
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            page_content = response.content
            soup = BeautifulSoup(page_content, 'lxml')
            paintings = soup.find_all('div', class_='sc-15ws6ki-0 wZWfg')
            for painting in paintings:
                name = painting.find('a', alt=True).text.strip()
                artist_link = painting.find('a', title=lambda title: title and 'View artist' in title)
                if artist_link:
                    artist = artist_link.get('title').split('View artist ')[1].split(' profile')[0]
                else:
                    artist = "Artist name not found"
                price = painting.find('div', {'data-type': 'prices', 'data-style': 'column'})
                price_usd = price.p.text.strip().replace('$', '').replace(',', '') if price else 'Price not found'
                all_data.append({'Name': name, 'Price': clean_price(f'${price_usd}'), 'Artist': artist})
        except requests.HTTPError as e:
            print(f"HTTP error occurred: {e}")
        except requests.RequestException as e:
            print(f"An error occurred: {e}")
        time.sleep(3)
    saatchiart_df = pd.DataFrame(all_data)
    return saatchiart_df

def update_data_store():
    print("Updating data store...")
    formart_df = scrape_formart()
    print("Scraped Formart website")
    zigguratss_df = scrape_zigguratss()
    zigguratss_df['Artist'] = zigguratss_df['Artist'].apply(clean_artist_name)
    print("Scraped Zigguratss website")
    artflute_df = scrape_artflute()
    print("Scraped Artflute website")
    fizdi_df = scrape_fizdi()
    fizdi_df['Artist'] = fizdi_df['Artist'].apply(clean_artist_name2)
    print("Scraped Fizdi website")
    mojarto_df = scrape_mojarto()
    print("Scraped Mojarto website")
    saatchiart_df = scrape_saatchiart()
    print("Scraped Saatchiart website")
    # combined_df = pd.concat([zigguratss_df, fizdi_df], ignore_index=True)
    combined_df = pd.concat([formart_df, zigguratss_df, artflute_df, fizdi_df, mojarto_df, saatchiart_df], ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=['Name', 'Artist', 'Price'])


    # Store all artwork names and artist names as pairs
    all_artworks_artists = list(zip(combined_df['Name'], combined_df['Artist']))

    # Find common artworks and artists pairs
    artworks_artists_count = pd.Series(all_artworks_artists).value_counts()
    common_artworks_artists = artworks_artists_count[artworks_artists_count > 1].index.tolist()

    # Print common artworks and artists pairs
    print("Common Artworks and Artists:")
    for name, artist in common_artworks_artists:
        print(f"Artwork: {name}, Artist: {artist}")

    # Update data store
    data_store['formart'] = formart_df
    data_store['zigguratss'] = zigguratss_df
    data_store['artflute'] = artflute_df
    data_store['fizdi'] = fizdi_df
    data_store['mojarto'] = mojarto_df
    data_store['saatchiart'] = saatchiart_df
    data_store['combined'] = combined_df

    print("Data store updated.")

@app.route('/artwork', methods=['GET'])
def get_artwork():
    artwork_name = request.args.get('name')
    artist_name = request.args.get('artist')

    if not artwork_name or not artist_name:
        return "Please provide both artwork name and artist name", 400

    filtered_df = pd.DataFrame()

    # Search in each dataframe in the data store excluding 'combined'
    for key, df in data_store.items():
        if key != 'combined' and not df.empty:
            # Filter by artwork name and artist name
            mask = (df['Name'].str.contains(artwork_name, case=False)) & (df['Artist'].str.contains(artist_name, case=False))
            filtered_results = df[mask].copy()

            if not filtered_results.empty:
                # Add a column for website name
                filtered_results['Website'] = key

                # Append filtered results to the final dataframe
                filtered_df = pd.concat([filtered_df, filtered_results], ignore_index=True)

    if filtered_df.empty:
        return {"message": "No matching artwork found."}, 404
    else:
        # Remove duplicates
        filtered_df = filtered_df.drop_duplicates(subset=['Name', 'Artist', 'Price'])

        return filtered_df.to_json(orient="records", force_ascii=False), 200
    

if __name__ == "__main__":
    # Start the scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_data_store, 'interval', hours=12)
    scheduler.start()

    # Initial data update
    update_data_store()

    # Run the Flask app
    app.run()
