
# coding: utf-8

import datetime as dt
import json
import pandas as pd
import random
import time
import urllib2
import yaml

# ref: https://github.com/har07/PySastrawi
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

try:
    with open('config.yml') as f:
        CONFIG = yaml.load(f)
except IOError:
    print 'Configuration file (config.yml) is missing. Please make one.'
    exit()
except:
    raise

API_TOKEN = CONFIG.get('telegram_token', False)
assert API_TOKEN, 'Telegram api token not found.'

BASE_URL = 'https://api.telegram.org/bot%s' % (API_TOKEN)

def create_stemmer():
    factory = StemmerFactory()
    stemmer = factory.create_stemmer()

    return stemmer
    
STEMMER = create_stemmer()

def get_dict():
    data_fn = r'data/kbbi_dataset.csv'
    df = pd.DataFrame()
    try:
        df = pd.read_csv(data_fn)
        df = df.astype(str)
    except IOError:
        print 'Make sure kbbi dataset available in "data" folder\n'\
              'You can clone it from this url:\n'\
              'https://github.com/bbn-bernard/kbbi_dataset'

    return df


DICT = get_dict()


def json_request(method, payload):
    url = '%s/%s' % (BASE_URL, method)
    payload_text = json.dumps(payload)

    request = urllib2.Request(url, payload_text)
    request.add_header('Content-Type', 'application/json')

    result = False
    try:
        res = urllib2.urlopen(request)
        result = res.read()
    except KeyboardInterrupt:
        raise
    except:
        pass

    return result

last_update_id = 0

while True:
    body = json_request('getUpdates', {'offset': last_update_id})
    updates = json.loads(body)

    if not updates:
        time.sleep(5)
        continue

    respond_text = ''
    for result in updates['result']:
        if result.get('message', False) and result['message'].get('entities', False):
            msg_text = result['message']['text']
            args = msg_text.split(' ')
            raw_command = args[0].lower()
            if len(args) > 1:
                query = args[1]
            else:
                query = False
            
            timestamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print '%s, %s, %s' % (raw_command, query, timestamp)
            
            # format: command@botname
            command = raw_command.split('@')[0]
            if command == '/help':
                respond_text = '''Perintah yang tersedia:                
/cari - cari kata yang diawali sepenggal kata
/arti - cari definisi kata menurut kbbi'''
                json_request('sendMessage', {'chat_id': result['message']['chat']['id'],
                                             'text': respond_text})
            if command == '/cari':
                respond_text = ''
                
                # restrict len of word
                if query and len(query) < 10:
                    w = query.lower()
                    df = DICT[DICT['kata_dasar'].str.startswith(w)]
                    if not df.empty:
                        respond_text = random.choice(df['kata_dasar'].values)
                    else:
                        respond_text = 'kata yang diawali "%s" tidak ditemukan' % (query)
                    json_request('sendMessage', {'chat_id': result['message']['chat']['id'],
                                                 'text': respond_text,
                                                 'reply_to_message_id': result['message']['message_id'],})
            # TODOS: refactor
            if command == '/arti':
                respond_text = ''
                
                # restrict len of word
                if query and len(query) < 20:
                    try:
                        w = STEMMER.stem(query.lower().encode('ascii'))
                        df = DICT[DICT['kata_dasar'].str.lower().str.strip() == w]
                    except:
                        df = pd.DataFrame()    
                    
                    if not df.empty:
                        respond_text = '_%s_\n' % (w)
                        respond_text += '```text\n'
                        for k,v in enumerate(df['arti']):
                            respond_text += '[%s] %s\n' % (k+1, v.decode('utf-8'))
                        # TODOS: limit string len
                        if len(respond_text) > 4000:
                            respond_text = respond_text[:4000] + '...'
                        respond_text += '```'
                    else:
                        respond_text = 'kata "%s" tidak ditemukan' % (query)

                    json_request('sendMessage', {'chat_id': result['message']['chat']['id'],
                                                 'text': respond_text,
                                                 'parse_mode': 'Markdown',})
                    
        last_update_id = int(result['update_id']) + 1
        
    time.sleep(1)



