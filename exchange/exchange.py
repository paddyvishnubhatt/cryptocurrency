import urllib2
import urllib
import logging
import datetime

import json

from flask import render_template

class Exchange:
    pass

def show_markets():
    exchange_names = ["BitfinexUSD",
                      "BitstampUSD",
                      "OKCoinUSD",
                      "KrakenUSD",
                      "GeminiUSD"]
    exchanges = get_exchanges(exchange_names)
    return render_template('exchanges.html',
                            exchanges=exchanges)

def get_exchanges(exchange_names):
    exchanges = []
    for iexchange in exchange_names:
        exchange = get_exchange(iexchange)
        if exchange:
            exchanges.append(exchange)
    return exchanges

def get_exchange(exchange_name):
    jsonstr = ""
    try:
        if exchange_name == 'BitstampUSD' or exchange_name == 'KrakenUSD' or exchange_name == 'OKCoinCNY':
            if exchange_name == 'KrakenUSD':
                url = 'https://api.kraken.com/0/public/Depth?pair=XXBTZUSD'
            elif exchange_name == 'BitstampUSD':
                url = 'https://www.bitstamp.net/api/order_book/'
            elif exchange_name == 'OKCoinUSD':
                url = 'https://www.okcoin.cn/api/depth.do?symbol=btc_usd'
            elif exchange_name == "GeminiUSD":
                url = 'https://api.gemini.com/v1/book/btcusd'

            req = urllib2.Request(url, None, headers={
                                        "Content-Type": "application/x-www-form-urlencoded",
                                        "Accept": "*/*",
                                        "User-Agent": "curl/7.24.0 (x86_64-apple-darwin12.0)"})

            res = urllib2.urlopen(req)
            jsonstr = res.read().decode('utf8')
            raw_exchange = json.loads(jsonstr)
            if raw_exchange:

                rexchange = Exchange()
                rexchange.name = exchange_name
                rexchange.cc = "BTC"
                rexchange.currency = "USD"

                if exchange_name == 'OKCoinUSD':
                    rexchange.price = raw_exchange.get('asks')[0][0]
                elif exchange_name == 'KrakenUSD':
                    rexchange.time  = raw_exchange.get('result').get('XXBTZUSD').get('asks')[0][2]
                    rexchange.price = raw_exchange.get('result').get('XXBTZUSD').get('asks')[0][0]
                elif exchange_name == 'GeminiUSD':
                    rexchange.price = raw_exchange.get('asks')[0][0]
                    rexchange.time = raw_exchange.get('asks')[0][2]
                else:
                    rexchange.time = long(raw_exchange.get('timestamp'))
                    rexchange.price = raw_exchange.get('asks')[0][0]

                rexchange.price = float("{0:.2f}".format(float(rexchange.price)))
                rexchange.time = datetime.datetime.utcfromtimestamp(rexchange.time).strftime('%Y-%m-%dT%H:%M:%SZ')

                return rexchange
            else:
                return None
        else:
            res = urllib.urlopen('https://api.bitfinex.com/v1/book/btcusd')
            jsonstr = res.read().decode('utf8')
            raw_exchange = json.loads(jsonstr)
            exchange = raw_exchange.get('asks')
            if exchange:
                rexchange = Exchange()
                rexchange.name = exchange_name
                rexchange.cc = "BTC"
                rexchange.time = str(exchange[0].get('timestamp')).split(".", 1)[0]
                rexchange.time = long(rexchange.time)
                rexchange.price = float("{0:.2f}".format(float(exchange[0].get('price'))))
                rexchange.currency = "USD"
                rexchange.time = datetime.datetime.utcfromtimestamp(rexchange.time).strftime('%Y-%m-%dT%H:%M:%SZ')
                return rexchange
            else:
                return None
    except Exception:
        logging.error("%s - Can't parse json: %s" % (exchange_name, jsonstr))
        return None

