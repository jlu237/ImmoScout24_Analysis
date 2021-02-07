#!/usr/bin/python
# coding: utf-8

# # Immoscout24.de Scraper
#
# Ein Script zum dumpen (in `.csv` schreiben) von Immobilien, welche auf [immoscout24.de](http://immoscout24.de) angeboten werden

# In[5]:
import pymongo
from bs4 import BeautifulSoup
import json
import urllib.request as urllib2
import random
from random import choice
import time
from datetime import datetime

import logging

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='immo_scraper.log',
                    level=logging.DEBUG)
logging.info('Scraper is starting.')

print("Scraper is starting.")

client = pymongo.MongoClient("mongodb://admin:admin123@dst-shard-00-00-xd93f.mongodb.net:27017,dst-shard-00-01-xd93f.mongodb.net:27017,dst-shard-00-02-xd93f.mongodb.net:27017/test?ssl=true&replicaSet=DST-shard-0&authSource=admin&retryWrites=true&w=majority")
db = client.IMMO_DATA
timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M')

col = db[timestamp]
logging.info('Data has been saved to MongoDB (new entry in Collection).')



# In[7]:

def urlquery(url):
    # function cycles randomly through different user agents and time intervals to simulate more natural queries
    try:
        sleeptime = float(random.randint(1, 6)) / 5
        time.sleep(sleeptime)

        agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1309.0 Safari/537.17',
            'Mozilla/5.0 (compatible; MSIE 10.6; Windows NT 6.1; Trident/5.0; InfoPath.2; SLCC1; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET CLR 2.0.50727) 3gpp-gba UNTRUSTED/1.0',
            'Opera/12.80 (Windows NT 5.1; U; en) Presto/2.10.289 Version/12.02',
            'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)',
            'Mozilla/3.0',
            'Mozilla/5.0 (iPhone; U; CPU like Mac OS X; en) AppleWebKit/420+ (KHTML, like Gecko) Version/3.0 Mobile/1A543a Safari/419.3',
            'Mozilla/5.0 (Linux; U; Android 0.5; en-us) AppleWebKit/522+ (KHTML, like Gecko) Safari/419.3',
            'Opera/9.00 (Windows NT 5.1; U; en)']

        agent = choice(agents)
        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', agent)]

        html = opener.open(url).read()
        time.sleep(sleeptime)

        return html

    except Exception as e:
        logging.info('Something went wrong with Crawling:\n%s' % e)


# In[9]:


def immoscout24parser(url):
    ''' Parser holt aus Immoscout24.de Suchergebnisseiten die Immobilien '''

    try:
        soup = BeautifulSoup(urlquery(url), 'html.parser')
        scripts = soup.findAll('script')
        for script in scripts:
            # print script.text.strip()
            if 'IS24.resultList' in script.text.strip():
                s = script.string.split('\n')
                for line in s:
                    # print('\n\n\'%s\'' % line)
                    if line.strip().startswith('resultListModel'):
                        resultListModel = line.strip('resultListModel: ')
                        immo_json = json.loads(resultListModel[:-1])

                        searchResponseModel = immo_json[u'searchResponseModel']
                        resultlist_json = searchResponseModel[u'resultlist.resultlist']

                        return resultlist_json

    except Exception as e:
        logging.info("Fehler in immoscout24 parser: %s" % e)


# ## Main Loop
#
# Geht Wohnungen und Häuser, jeweils zum Kauf und Miete durch und sammelt die Daten

# In[31]:


immos = {}

b = 'Berlin'  # Bundesland
s = 'Berlin'  # Stadt
k = 'Wohnung'  # Wohnung oder Haus
w = 'Miete'  # Miete oder Kauf

page = 0
logging.info('Suche %s / %s' % (k, w))

while True:
    page += 1
    url = 'https://www.immobilienscout24.de/Suche/S-T/P-%s/%s-%s/%s/%s?pagerReporting=true' % (page, k, w, b, s)

    # Because of some timeout or immoscout24.de errors,
    # we try until it works \o/
    resultlist_json = None
    while resultlist_json is None:
        try:
            resultlist_json = immoscout24parser(url)
            numberOfPages = int(resultlist_json[u'paging'][u'numberOfPages'])
            pageNumber = int(resultlist_json[u'paging'][u'pageNumber'])
        except:
            pass

    if page > 2:
        break

    # Get the data
    for resultlistEntry in resultlist_json['resultlistEntries'][0][u'resultlistEntry']:
        realEstate_json = resultlistEntry[u'resultlist.realEstate']

        realEstate = {}

        realEstate[u'Miete/Kauf'] = w
        realEstate[u'Haus/Wohnung'] = k

        realEstate['address'] = realEstate_json['address']['description']['text']
        realEstate['city'] = realEstate_json['address']['city']
        realEstate['postcode'] = realEstate_json['address']['postcode']
        realEstate['quarter'] = realEstate_json['address']['quarter']
        try:
            realEstate['lat'] = realEstate_json['address'][u'wgs84Coordinate']['latitude']
            realEstate['lon'] = realEstate_json['address'][u'wgs84Coordinate']['longitude']
        except:
            realEstate['lat'] = None
            realEstate['lon'] = None

        realEstate['title'] = realEstate_json['title']

        realEstate['numberOfRooms'] = realEstate_json['numberOfRooms']
        realEstate['livingSpace'] = realEstate_json['livingSpace']

        if k == 'Wohnung':
            realEstate['balcony'] = realEstate_json['balcony']
            realEstate['builtInKitchen'] = realEstate_json['builtInKitchen']
            realEstate['garden'] = realEstate_json['garden']
            realEstate['price'] = realEstate_json['price']['value']
            realEstate['privateOffer'] = realEstate_json['privateOffer']
        elif k == 'Haus':
            realEstate['isBarrierFree'] = realEstate_json['isBarrierFree']
            realEstate['cellar'] = realEstate_json['cellar']
            realEstate['plotArea'] = realEstate_json['plotArea']
            realEstate['price'] = realEstate_json['price']['value']
            realEstate['privateOffer'] = realEstate_json['privateOffer']

        realEstate['floorplan'] = realEstate_json['floorplan']
        realEstate['from'] = realEstate_json['companyWideCustomerId']
        realEstate['ID'] = realEstate_json[u'@id']
        realEstate['url'] = u'https://www.immobilienscout24.de/expose/%s' % realEstate['ID']

        immos[realEstate['ID']] = realEstate



    #col.insert_one(immos)

    logging.info('Scrape Page %i/%i (%i Immobilien %s %s gefunden)' % (page, numberOfPages, len(immos), k, w))

# In[32]:


logging.info("Scraped %i Immos" % len(immos))

# ## Datenaufbereitung & Cleaning
#
# Die gesammelten Daten werden in ein sauberes Datenformat konvertiert, welches z.B. auch mit Excel gelesen werden kann. Weiterhin werden die Ergebnisse pseudonymisiert, d.h. die Anbieter bekommen eindeutige Nummern statt Klarnamen.

# In[33]:



timestamp = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M')

# In[34]:


import pandas as pd

# In[35]:

df = pd.DataFrame(immos).T
df.index.name = 'ID'

# In[36]:
col.insert_many(df.to_dict("records"))

logging.info('Scraper is finished.')

print("Scraper is finished.")
