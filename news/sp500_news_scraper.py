from datetime import datetime

import requests
import bs4 as bs
import pandas as pd


# Pulls the top k headlines for a company via Google News within a date range
def get_headlines(company_name, start_date=None, end_date=None, limit=50):

    query = company_name
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        query += f"%20after%3A{start_date}"
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        query += f"%20before%3A{end_date}"
    url = f"https://news.google.com/search?q={query}&hl=en-US&gl=US&ceid=US%3Ae"

    response = requests.get(url)
    headlines = []
    if response.status_code != 200:
        return headlines

    soup = bs.BeautifulSoup(response.content, 'html.parser')
    for item in soup.find_all(class_='JtKRv', limit=limit):
        headlines.append(item.get_text())

    print(headlines)
    return headlines


# Fetches the S&P 500 companies from Wikipedia
def get_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url)
    if response.status_code != 200:
        return []

    soup = bs.BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'class': 'wikitable sortable'}, id='constituents')

    data = []
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        ticker = cols[0].text.strip()
        name = cols[1].text.strip()
        if 'Class' in name:
            name = name[:-10]
        gics_sector = cols[3].text.strip()
        gics_subsector = cols[4].text.strip()
        data.append([ticker, name, gics_sector, gics_subsector])

    return pd.DataFrame(data, columns=['Ticker', 'Name', 'GICS Sector', 'GICS Subsector'])


# Add the top headlines to the dataframe and out to csv
# sp500 = get_sp500()
# sp500['Headlines'] = sp500['Name'].apply(get_headlines)
#
# sp500.to_csv('sp500.csv', index=False)

# test getting headlines from crowdstrike in july 2024

get_headlines('Apple', '2004-07-01', '2004-07-31')


