
import re
from datetime import datetime
import time
import os
from random import choice

import bs4 as bs
import contractions
import nltk
import pandas as pd
import requests
from nltk.corpus import stopwords
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from num2words import num2words

nltk.download('wordnet', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)


# Pulls the top k headlines for a company via Google News within a date range
def get_headlines(company_name, start_date=None, end_date=None, limit=75):

    query = company_name.replace(' ', '%20')
    if start_date:
        query += f"%20after%3A{start_date}"
        if not end_date:
            # if only start date is provided, set end date to 24h after start
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = (start_date + pd.DateOffset(days=1)).strftime('%Y-%m-%d')
    if end_date:
        query += f"%20before%3A{end_date}"

    url = f"https://news.google.com/search?q={query}&hl=en-US&gl=US&ceid=US%3Ae"
    print(f"Scraping headlines for {company_name} from {start_date} to {end_date}: {url}")
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
    ]
    headers = {'User-Agent': choice(user_agents)}
    response = requests.get(url, headers=headers)
    headlines = []

    if response.status_code != 200:
        print('response code not 200:' + str(response.status_code))
        print(f'headlines for {company_name} on {start_date} : {headlines}')
        return headlines

    soup = bs.BeautifulSoup(response.content, 'html.parser')
    for item in soup.find_all(class_='JtKRv', limit=limit):
        headlines.append(preprocess_headline(item.get_text()))

    print(f'headlines for {company_name} on {start_date} : {headlines}')
    return headlines

# Preprocesses the headline text
def preprocess_headline(headline):
    def replace_numbers_and_percentages(text):
        """
        Replace all numbers and percentages in a string with their English word equivalents.
        """
        number_pattern = re.compile(r'(\d+(\.\d+)?%?)')

        def convert_number_to_words(match):
            """
            Convert a matched number or percentage to words.
            """
            number_str = match.group(0)

            if '%' in number_str:
                # Handle percentages
                number = float(number_str.replace('%', ''))
                number_in_words = num2words(number) + ' percent'
            else:
                # Handle regular numbers (integers or floats)
                number = float(number_str)
                number_in_words = num2words(number)

            return number_in_words

        # Replace numbers and percentages in the text with their word equivalents
        text_with_words = number_pattern.sub(convert_number_to_words, text)
        return text_with_words

    def get_wordnet_pos(treebank_tag):
        """
        Convert TreeBank POS tags to WordNet POS tags for lemmatization.
        """
        if treebank_tag.startswith('J'):
            return wordnet.ADJ
        elif treebank_tag.startswith('V'):
            return wordnet.VERB
        elif treebank_tag.startswith('N'):
            return wordnet.NOUN
        elif treebank_tag.startswith('R'):
            return wordnet.ADV
        else:
            return wordnet.NOUN

    def remove_stop_words():
        stop_words = set(stopwords.words('english')) - negation_words
        return [word for word in toks if word not in stop_words]

    def lemmatize_tokens():
        lemmatizer = WordNetLemmatizer()
        pos_tags = nltk.pos_tag(toks)
        lemmatized_toks = []
        for token, pos in pos_tags:
            lemma = lemmatizer.lemmatize(token, get_wordnet_pos(pos))
            lemmatized_toks.append(lemma)
        return lemmatized_toks

    def handle_negation():
        negated_toks = []
        negate = False
        for token in toks:
            if token in negation_words:
                negate = True
                continue
            if negate:
                negated_toks.append('not_' + token)
                negate = False
            else:
                negated_toks.append(token)
        return negated_toks

    negation_words = {'not', 'no', 'never', 'neither', 'nor', 'nobody', "n't"}
    # Convert to lowercase
    headline = headline.lower()
    # Expand contractions
    headline = contractions.fix(headline)
    # convert numbers to words
    headline = replace_numbers_and_percentages(headline)
    # Remove punctuation
    headline = re.sub(r'[^\w\s]', '', headline)
    # Tokenize the text
    toks = nltk.word_tokenize(headline)
    # Remove stop words, excluding negation
    toks = remove_stop_words()
    # Lemmatize the tokens
    toks = lemmatize_tokens()
    # Handle negation
    toks = handle_negation()

    return ' '.join(toks)

# Fetches the S&P 100 companies from Wikipedia
def get_sp100():
    url = "https://en.wikipedia.org/wiki/S%26P_100"
    response = requests.get(url)
    if response.status_code != 200:
        return []

    soup = bs.BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'class': 'wikitable sortable'}, id='constituents')

    data = []
    seen_names = set()
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        ticker = cols[0].text.strip()
        name = cols[1].text.strip()
        if 'Class' in name:
            name = name[:-10]
        if name[-1] == ')':
            name = name[name.rfind('(') + 1: name.rfind(')')] + ' ' + name[:name.rfind('(')]
        if name in seen_names:
            continue
        seen_names.add(name)
        gics = cols[2].text.strip()
        data.append([ticker, name, gics])

    return pd.DataFrame(data, columns=['Ticker', 'Name', 'GICS'])

def scrape_data():
    sp100 = get_sp100()['Name']
    for index, company in enumerate(sp100[:1]): # change to sp100 to scrape all companies
        os.makedirs(f'data/{company}', exist_ok=True)
        df = pd.DataFrame(columns=['Date', 'Headlines'])
        print(f'Working on company {index+1} : {company}')
        for year in range(2019, 2024):
            for month in range(1, 13):
                day_range = 31
                if month in [4, 6, 9, 11]:
                    day_range = 30
                elif month == 2:
                    day_range = 29 if year % 4 == 0 else 28

                day = 1
                while day <= day_range:
                    start_date = f'{year}-{month:02d}-{day:02d}'
                    end_date = f'{year}-{month:02d}-{min(day+6, day_range):02d}'
                    if start_date == end_date:
                        break

                    headlines = get_headlines(company, start_date, end_date)
                    if not headlines:
                        print(f"No headlines found for {company} from {start_date} to {end_date}")
                        print('Waiting 5 minutes before trying again...')
                        time.sleep(300)
                        headlines = get_headlines(company, start_date, end_date)
                        if not headlines:
                            print(f'FAILURE FOR {company} from {start_date} to {end_date}')

                    df.loc[len(df.index)] = [start_date, headlines]
                    day += 7

        df.to_csv(f'data/{company}/headlines.csv', index=False)

scrape_data()


