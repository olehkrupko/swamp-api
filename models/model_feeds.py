import feedparser
import json
import os
import random
import ssl
import string
import urllib
from datetime import datetime, timedelta
from dateutil import parser, tz  # adding custom timezones
from typing import List, Dict

import pika
import requests
import sentry_sdk
from bs4 import BeautifulSoup, SoupStrainer
from sqlalchemy.dialects.postgresql import JSONB

from __main__ import db, FREQUENCIES
from models.model_feeds_update import Update


class Feed(db.Model):
    __table_args__ = {
        "schema": "feed_updates",
    }

    # technical
    _id        = db.Column(db.Integer,     primary_key=True)
    _created  = db.Column(db.DateTime,    default=datetime.utcnow)
    _delayed  = db.Column(db.DateTime,    default=None)
    # core/required
    title     = db.Column(db.String(100), unique=True,  nullable=False)
    href      = db.Column(db.String(200), unique=False, nullable=False)
    href_user = db.Column(db.String(200), unique=False, nullable=True)
    # metadata
    private   = db.Column(db.Boolean,     default=False  )
    frequency = db.Column(db.String(20),  default='weeks')
    notes     = db.Column(db.String(200), default='',   nullable=True, unique=False)
    json      = db.Column(JSONB)

    def __init__(self, data: dict):
        data = data.copy()
        if not isinstance(data, dict):
            raise Exception(f"__init__ data {data} has to be a dict, not {type(data)}")

        self.title = data.pop('title')
        self.href = data.pop('href')
        self.href_user = data.pop('href_user')

        self.private = data.pop('private')
        frequency = data.pop('frequency')
        if frequency in FREQUENCIES:
            self.frequency = frequency
        else:
            raise Exception(f"Frequency {frequency} is not in {FREQUENCIES}")
        self.notes = data.pop('notes')
        self.json = data.pop('json')

        if data:
            raise Exception(f"Dict {data} has extra data")
    
    def as_dict(self) -> dict:
        return {
            '_id': self._id,

            'title': self.title,
            'href': self.href,
            'href_user': self.href_user,

            'private': self.private,
            'frequency': self.frequency,
            'notes': self.notes,
            'json': self.json,
        }

    def __str__(self):
        return str(self.as_dict())
    
    def requires_update(self):
        if self.frequency == 'never':
            return False

        if not self._delayed:
            return True
        elif self._delayed <= datetime.now():
            return True
        
        return False

    ####################################################
    ####          FEED PARSING LOGIC BELOW          ####
    ####################################################

    def parse_list(self, results: List[Dict]):
        return results
    
    @staticmethod
    def process_parsing(feed_id, store_new=True, proxy=False):
        # Preparing
        new_items = []
        feed = db.session.query(Feed).filter_by(
            _id=feed_id,
        ).first()
        feed_len = db.session.query(Update).filter_by(
            feed_id=feed_id,
        ).count()

        # Processing
        feed_updates = feed.parse_href(
            proxy  = proxy,
        )

        # Finishing with results
        if store_new:
            for each in feed_updates:
                if db.session.query(Update).filter_by(
                    feed_id=feed_id,
                    href=each['href'],
                ).count() == 0:
                    new_update = Update(each)
                    if new_update.filter_skip(json=feed.json):
                        continue
                    if feed_len != 0:
                        new_update.datetime = datetime.now()
                    db.session.add(new_update)
                new_items.append(each)
            feed._delayed = datetime.now() + timedelta(**{
                feed.frequency: random.randint(1, 10),
            })
            db.session.add(feed)
            db.session.commit()
        else:
            new_items = feed_updates.copy()
        
        # Return data
        return {
            "len":  len(new_items),
            "items":    new_items,
            "feed":     feed,
        }
    
    @staticmethod
    def process_parsing_multi(force_all=False, store_new=True, proxy=False):
        results = 0
        feed_todo_ids = []
        feed_list = db.session.query(Feed).all()
        random.shuffle(feed_list)

        for feed in feed_list:
            if feed.frequency not in FREQUENCIES:
                raise ValueError(f"Feed { feed.title }'s frequency is invalid. Feed dict: { feed.as_dict() }")
            elif force_all or feed.requires_update():
                feed_todo_ids.append(feed._id)
        
        for feed_id in feed_todo_ids:
            results += Feed.process_parsing(
                feed_id=feed_id,
                store_new=store_new,
                proxy=proxy,
            )['len']

        # with Executor() as executor:
        #     executor = executor.map(Feed.process_parsing, feed_todo_ids, [store_new]*len(feed_todo_ids), [proxy]*len(feed_todo_ids))
        #     if options['logBar']:
        #         executor = tqdm(executor, total=len(parse_feeds))

        #     for result in executor:
        #         print(result['len'])
        #         if options['logEach'] or (options["logEmpty"] and result['amount_total'] == 0):
        #             Command.print_feed(
        #                 title=result['title'], 
        #                 amount=result['amount'], 
        #                 time=result['time']
        #             )
                
        #         if options['log']:
        #             total_items += result['amount']

        return results
    
    @staticmethod
    def process_parsing_multi_queue(force_all=False, store_new=True, proxy=False):
        feed_list = db.session.query(Feed).all()
        random.shuffle(feed_list)
        feed_list = filter(lambda x: x.requires_update(), feed_list)

        for feed in feed_list:
            params = pika.URLParameters(os.environ['RABBITMQ_CONNECTION_STRING'])
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            channel.basic_publish(
                exchange='swamp',
                routing_key='feed-parser',
                body=json.dumps(
                    feed.as_dict()
                ),
            )

    def parse_href(self, href = None, proxy: bool = True, **kwargs: Dict):
        #######################################
        ####  PREPARING REQUIRED VARIABLES ####
        #######################################
        results = []
        if href is None:
            href = self.href

        # avoiding blocks
        headers = {
            # 'user-agent': feed.UserAgent_random().strip(),
            'referer': f'https://www.{ "".join(random.choices(string.ascii_letters, k=16)) }.com/?q={ href }'
        }
        proxyDict = {}
        if proxy and isinstance(proxy, str):
            proxyDict["http"]  = "http://"  + proxy
            proxyDict["https"] = "https://" + proxy

        #######################################
        ####    STARTING DATA INGESTION    ####
        #######################################

        # using it as first if for now
        if False:
            return "NOPE"

        # # custom ранобэ.рф API import
        # if 'https://xn--80ac9aeh6f.xn--p1ai' in self.href:
        #     RANOBE_RF = 'https://xn--80ac9aeh6f.xn--p1ai'
        #     slug = self.href[31:-1]

        #     request = f"{ RANOBE_RF }/v3/books/view?slug={ slug }"
        #     request = requests.get(request).json()  # (request, headers=headers, proxies=proxyDict)
        #     id = request['id']
            
        #     request = f"{ RANOBE_RF }/v3/chapters?filter[bookId]={ id }"
        #     request = requests.get(request).json()  # (request, headers=headers, proxies=proxyDict)

        #     for each in request['items']:
        #         if not each['isDonate']:  # ignoring payed chapters
        #             result.append(Update(
        #                 name=each["title"],
        #                 href=RANOBE_RF + each["url"],
        #                 datetime=datetime.strptime(each["publishedAt"], '%Y-%m-%d %H:%M:%S'),
        #                 title=self.title))

        # # custom instagram import ( OLD, use in really rare cases )
        # elif 'https://www.instagram.com/' in self.href:
        #     try:
        #         request = requests.get(self.href, headers=headers, proxies=proxyDict)
        #         request = BeautifulSoup(request.text, "html.parser")

        #         for each in request.find_all('script'):
        #             print('>>>>', each)
        #             data = 'window._sharedData = '
        #             if str(each).find(data) != -1:
        #                 # preparing JSON
        #                 data = str(each).find(data) + len(data)  # data start position
        #                 data = str(each)[data:-10]  # -1 is for removing ; in the end
        #                 data = json.loads(data)

        #                 # selecting data from JSON
        #                 data = data['entry_data']['ProfilePage'][0]['graphql']
        #                 data = data['user']['edge_owner_to_timeline_media']['edges']

        #                 # parsing data from JSON
        #                 for each in data:
        #                     # avoiding errors caused by empty titles
        #                     try:
        #                         result_name = each['node']['edge_media_to_caption']['edges'][0]['node']['text']
        #                     except IndexError:
        #                         result_name = 'no title'

        #                     results.insert(0, {
        #                         'name':     result_name,
        #                         'href':     "https://www.instragram.com/p/"+each['node']['shortcode']+"/",
        #                         'datetime': datetime.fromtimestamp(each['node']['taken_at_timestamp']),
        #                         'feed_id':  self.id,
        #                     })
        #     except (KeyError, requests.exceptions.ProxyError, requests.exceptions.SSLError):
        #         return []

        # # custom instagram import converter
        # elif 'https://www.instagram.com/' in self.href:
        #     self.href_user = self.href[:]
        #     # caching server list: https://git.sr.ht/~cadence/bibliogram-docs/tree/master/docs/Instances.md
        #     caching_servers = (
        #         'https://bibliogram.snopyta.org',
        #         'https://bibliogram.nixnet.services',  # x
        #         'https://bg.endl.site',
        #         'https://bibliogram.pixelfed.uno',
        #         'https://bibliogram.ethibox.fr',
        #         'https://ig.funami.tech',
        #         'https://bibliogram.hamster.dance',  # x
        #     )
        #     # 26 = len('https://www.instagram.com/')
        #     # 1 = len('/')
        #     self.href = f"{ random.choice(caching_servers) }/u/{ self.href[26:-1] }/atom.xml"

        #     try:
        #         result = self.parse(proxy)
        #     except:
        #         return []

        #     base_domain = 'instagram.com'
        #     for each in result:
        #         # href: replace parser's domain name
        #         each.href = each.href.replace('http://', 'https://')
        #         href_split = each.href.split('/')
        #         href_split[2] = base_domain
        #         each.href = '/'.join(href_split) + '/'

        #         # title: remove hashtags
        #         each.title = each.title.replace('#', ' #')
        #         title_split = each.title.split(' ')
        #         title_split = [ x for x in title_split if x[0]!='#']
        #         each.title = ' '.join(title_split)

        # # custom twitter import converter
        # elif 'https://twitter.com/' in self.href:
        #     self.href_user = self.href[:]
        #     caching_servers = (
        #         'https://nitter.net',
        #         'https://nitter.42l.fr',  # +
        #         'https://nitter.nixnet.services',  # x
        #         'https://nitter.pussthecat.org',
        #         'https://nitter.mastodont.cat',
        #         'https://nitter.tedomum.net',  # xx
        #         'https://nitter.fdn.fr',
        #         'https://nitter.1d4.us',
        #         'https://nitter.kavin.rocks',
        #         'https://tweet.lambda.dance',  # xx
        #         'https://nitter.cc',
        #         'https://nitter.weaponizedhumiliation.com',  # x
        #         'https://nitter.vxempire.xyz',
        #         'https://nitter.unixfox.eu',
        #         'https://nitter.himiko.cloud',  # x
        #         'https://nitter.eu',
        #         'https://nitter.ethibox.fr',   # x
        #         'https://nitter.namazso.eu',  # +
        #     )
        #     # 20 = len('https://twitter.com/')
        #     self.href = f"{ random.choice(caching_servers) }/{ self.href[20:] }/rss"

        #     try:
        #         results = self.parse_href(proxy)
        #     except:
        #         return []

        #     base_domain = 'twitter.com'
        #     for each in results:
        #         each['href'] = each['href'].replace('#m', '').replace('http://', 'https://')
                
        #         href_split = each['href'].split('/')
        #         href_split[2] = base_domain

        #         each['href'] = '/'.join(href_split)

        # custom tiktok import
        elif 'https://www.tiktok.com/@' in href:
            href = f"https://proxitok.pabloferreiro.es/@{ href.split('@')[-1] }/rss"
            
            results = self.parse_href(
                href = href,
                proxy = proxy,
            )

            results.reverse()
            for each in results:
                each['href'] = each['href'].replace('proxitok.pabloferreiro.es', 'tiktok.com')

        # custom RSS YouTube converter (link to feed has to be converted manually)
        elif 'https://www.youtube.com/channel/' in href:
            # 32 = len('https://www.youtube.com/channel/')
            # 7 = len('/videos')
            href = "https://www.youtube.com/feeds/videos.xml?channel_id=" + href[32:-7]

            results = self.parse_href(
                href = href,
                proxy = proxy,
            )

        # custom RSS readmanga converter (link to feed has to be converted manually to simplify feed object creation)
        elif 'http://readmanga.live/' in href and href.find('/rss/') == -1:
            # 22 = len('http://readmanga.live/')
            name = href[22:]
            href = "feed://readmanga.live/rss/manga?name=" + name

            results = self.parse_href(
                href = href,
                proxy = proxy,
            )

            for each in results:
                split = each['href'].split('/')
                split[-3] = name
                each['href'] = '/'.join(split)

        # custom RSS mintmanga converter (link to feed has to be converted manually to simplify feed object creation)
        elif 'http://mintmanga.com/' in href and href.find('mintmanga.com/rss/manga') == -1 and kwargs.get('processed', False):
            # 21 = len('http://mintmanga.com/')
            name = href[21:]
            href = "feed://mintmanga.com/rss/manga?name=" + name

            results = self.parse_href(
                href = href,
                proxy = proxy,
                processed = True,
            )

            for each in results:
                split = each['href'].split('/')
                split[-3] = name
                each['href'] = '/'.join(split)

        # custom RSS deviantart converter (link to feed has to be converted manually to simplify feed object creation)
        elif 'https://www.deviantart.com/' in href and kwargs.get('processed', False):
            # 27 = len('https://www.deviantart.com/')
            # 9 = len('/gallery/')
            href = href[27:-9]
            href = f"https://backend.deviantart.com/rss.xml?type=deviation&q=by%3A{ href }+sort%3Atime+meta%3Aall"
            
            results = self.parse_href(
                href = href,
                proxy = proxy,
                processed = True,
            )

        # # custom pikabu import
        # elif 'pikabu.ru/@' in self.href:
        #     # try:
        #     strainer = SoupStrainer('div', attrs={'class': 'stories-feed__container'})

        #     try:
        #         request = requests.get(self.href, headers=headers, proxies=proxyDict)
        #     except requests.exceptions.SSLError:
        #         return []
        #     request = BeautifulSoup(request.text, "html.parser", parse_only=strainer)

        #     for each in request.find_all('article'):
        #         try:
        #             result_datetime = each.find('time')['datetime'][:-3]+"00"
        #             result_datetime = datetime.strptime(result_datetime, '%Y-%m-%dT%H:%M:%S%z')

        #             result.append(Update(
        #                 name=each.find('h2', {'class': "story__title"}).find('a').getText(),
        #                 href=each.find('h2', {'class': "story__title"}).find('a')['href'],
        #                 datetime=result_datetime,
        #                 title=self.title))

        #         except (TypeError, AttributeError) as err:
        #             # advertisement, passing as no need to save it
        #             pass
        #     # except (requests.exceptions.ConnectionError, requests.exceptions.SSLError) as err:
        #     #     # failed connection, hope it works from time to time
        #     #     return []

        # custom onlyfans import
        elif 'https://onlyfans.com/' in href:
            return []
        
        # custom patreon import
        elif 'https://www.patreon.com/' in href:
            return []

        # # custom lightnovelpub import
        # elif 'https://www.lightnovelpub.com/' in href:
        #     request = requests.get(href, headers=headers, proxies=proxyDict)
        #     request = BeautifulSoup(request.text, "html.parser")

        #     data = request.find('ul', attrs={'class': 'chapter-list'})
        #     if data is None:
        #         return []
            
        #     for each in data.find_all('li'):
        #         results.append({
        #             'name':     each.find('a')['title'],
        #             'href':     'https://www.lightnovelpub.com' + each.find('a')['href'],
        #             'datetime': datetime.strptime(each.find('time')['datetime'], '%Y-%m-%d %H:%M'),
        #             'feed_id':  self.id,
        #         })

        # default RSS import
        else:
            try:
                request = feedparser.parse(href, request_headers=headers)
            except urllib.error.URLError:
                proxyDict = urllib.request.ProxyHandler(proxyDict)

                ssl._create_default_https_context = ssl._create_unverified_context
                request = feedparser.parse(href, request_headers=headers, handlers=[proxyDict])

            for each in request["items"]:
                if not each:
                    raise DeprecationWarning(f"Data returned by {'active' if self.requires_update() else 'disabled'} feed {self} is empty, skipping iteration")
                    continue
                result_href = each["links"][0]["href"]

                # DATE RESULT: parsing dates
                if "published" in each:
                    result_datetime = each["published"]
                elif "delayed" in each:
                    result_datetime = each["delayed"]
                elif "updated" in each:
                    result_datetime = each["updated"]
                else:
                    print(f"result_datetime broke for { self.title }")
                
                tzinfos = {
                    'PDT': tz.gettz("America/Los_Angeles"),
                    'PST': tz.gettz("America/Juneau"),
                }
                if result_datetime.isdigit():
                    result_datetime = datetime.utcfromtimestamp(int(result_datetime))
                elif not isinstance(result_datetime, datetime):
                    result_datetime = parser.parse(result_datetime, tzinfos=tzinfos)

                if each.get("title_detail"):
                    result_name = each["title_detail"]["value"]
                else:
                    result_name = ""

                # APPEND RESULT
                results.append({
                    'name':     result_name,
                    'href':     result_href,
                    'datetime': result_datetime,
                    'feed_id':  self._id,
                })

        return self.parse_list(results=results)
