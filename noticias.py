from bs4 import BeautifulSoup
import requests as req
import json
from httpx import Client
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from collections import defaultdict 

# [Portal de Notícias] -> [Editoriais] -> [Fonte] 
sources = {
    'cnn': {
        'Mundo':        'https://www.cnnbrasil.com.br/internacional/',
        'Educação':     'https://www.cnnbrasil.com.br/?s=educa%C3%A7%C3%A3o&orderby=date&order=desc',
        'Política':     'https://www.cnnbrasil.com.br/politica/',
        'Pop_Arte_TV':  'https://www.cnnbrasil.com.br/pop/',
        'Viagem':       'https://www.cnnbrasil.com.br/viagemegastronomia/',
        'Tecnologia':   'https://www.cnnbrasil.com.br/tecnologia/'
    },
    'g1': {
        'Mundo':        'https://g1.globo.com/rss/g1/mundo/',
        'Educação':     'https://g1.globo.com/rss/g1/educacao/',
        'Política':     'https://g1.globo.com/rss/g1/politica/',
        'Pop_Arte_TV':  'https://g1.globo.com/rss/g1/pop-arte/',
        'Viagem':       'https://g1.globo.com/rss/g1/turismo-e-viagem/',
        'Tecnologia':   'https://www.cnnbrasil.com.br/tecnologia/'
    },
    'r7': {
        'Mundo':        'https://noticias.r7.com/internacional/feed.xml',
        'Educação':     'https://noticias.r7.com/educacao/feed.xml',
        'Política':     'https://noticias.r7.com/politica/feed.xml',
        'Pop_Arte_TV':  'https://entretenimento.r7.com/famosos-e-tv/feed.xml',
        'Viagem':       'https://entretenimento.r7.com/viagens/feed.xml',
        'Tecnologia':   'https://noticias.r7.com/tecnologia-e-ciencia/feed.xml'
    },
    'uol': {
        'Mundo':        'https://noticias.uol.com.br/internacional/',
        'Educação':     'https://educacao.uol.com.br/',
        'Política':     'https://noticias.uol.com.br/politica/',
        'Pop_Arte_TV':  'https://www.uol.com.br/splash/musica/pop/',
        'Viagem':       'https://www.uol.com.br/nossa/viagem/',
        'Tecnologia':   'https://www.uol.com.br/tilt/'
    }
}
lines = []
client = Client(
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,lt;q=0.8,et;q=0.7,de;q=0.6",
    },
    follow_redirects=True,
    http2=True,
)

def predict(title):
    # Caso deseje realizar previsão, favor configurar aplicação abaixo
    # https://github.com/mkuchak/sentiment-analysis/tree/master
    response = req.post('http://localhost:8000/predict', json={'text':title})
    return json.loads(response.text)
    # return {    
    #     'probabilities': { 'negative': .1, 'neutral':  .3, 'positive': .6 },
    #     'sentiment': 'positive', 
    #     'confidence': .6
    # }

def add_line(source, category, title):
    result = predict(title)
    line = {
            'source': source,
            'category': category, 
            'title': title, 
            'negative': result['probabilities']['negative'],
            'neutral': result['probabilities']['neutral'],
            'positive': result['probabilities']['positive'],
            'sentiment': result['sentiment'], 
            'confidence': result['confidence']
    }
    lines.append(line)

def scraper_cnn(category, response):
    soup = BeautifulSoup(response, 'html.parser')
    items = soup.find_all('div', {'class': 'home__list__news'})
    for i in items[:9]:
        title = i.div.h3.text
        add_line('cnn', category, title)
    if len(items) == 0:
        items = soup.find_all('li', {'class': 'home__list__item'})
    for i in items[:9]:
        title = i.h3.text.strip()
        add_line('cnn', category, title)

def scraper_g1(category, response):
    soup = BeautifulSoup(response, 'xml')
    items = soup.find_all('item')
    for i in items[:9]:
        title = i.title.text
        add_line('g1', category, title)

def scraper_r7(category, response):
    soup = BeautifulSoup(response, 'xml')
    items = soup.find_all('entry')
    for i in items[:9]:
        title = i.title.text
        add_line('r7', category, title)

def scraper_uol(category, response):
    soup = BeautifulSoup(response, 'html.parser')
    items = soup.find_all('div', {'class': 'thumb-caption'})
    for i in items[:9]:
        title = i.h3.text
        add_line('uol', category, title)

def init():
    for source in sources:
        print("######## Scraping " + source)
        for category in sources[source]:
            print("\t" + category + "...")
            url = sources[source][category]
            response = client.get(url)
            func = globals()['scraper_' + source]
            func(category, response.text)
    print('ok....')
    now = datetime.now()
    df = pd.DataFrame(lines)
    df.to_csv('noticias_{}.csv'.format(now.strftime("%Y-%m-%d_%H_%M_%S")), index=False)
    exit()

def graph(csv_file):
    df = pd.read_csv(csv_file)
    df.drop(['title', 'sentiment', 'confidence'], axis=1, inplace=True)
    grouped = df.groupby(['source', 'category']).mean()
    columns=['source', 'negative', 'neutral', 'positive']
    data = defaultdict(lambda: [])
    for index, row in grouped.iterrows():
        data[row.name[1]].append([row.name[0], row['negative'], row['neutral'], row['positive']])
    figure, axes = plt.subplots(1, 6, constrained_layout=True)
    for idx, row in enumerate(data):
        temp = pd.DataFrame(data[row], columns=columns)
        ax = temp.plot(x='source', title=row, kind='bar', stacked=True, yticks=[0,1], width=.7,
                xlabel='', legend=False, ax=axes[idx], color=['red', 'orange', 'green'], figsize=(10, 4))    
    plt.savefig('noticias_analise.png')

###############################################################################
# Instruções ##################################################################
###############################################################################

# Rodar o Scraping
#init()

# Gerar o gráfico (noticas_analise.png)
graph('noticias_2023-10-19_14_01_34.csv')