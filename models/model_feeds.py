import feedparser
import json
import os
import random
import ssl
import string
import urllib
from datetime import datetime
from dateutil import parser, tz  # adding custom timezones
from dateutil.relativedelta import relativedelta
from typing import List, Dict

import pika
from sentry_sdk import capture_message
from sqlalchemy.dialects.postgresql import JSONB

from __main__ import db, FREQUENCIES
from models.model_feeds_update import Update

# import requests
# from bs4 import BeautifulSoup, SoupStrainer


class Feed(db.Model):
    __table_args__ = {
        "schema": "feed_updates",
    }

    # technical
    _id = db.Column(
        db.Integer,
        primary_key=True,
    )
    _created = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )
    _delayed = db.Column(
        db.DateTime,
        default=None,
    )
    # core/required
    title = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
    )
    href = db.Column(
        db.String(200),
        unique=False,
        nullable=False,
    )
    href_user = db.Column(
        db.String(200),
        unique=False,
        nullable=True,
    )
    # metadata
    private = db.Column(
        db.Boolean,
        default=False,
    )
    frequency = db.Column(
        db.String(20),
        default="weeks",
    )
    notes = db.Column(
        db.String(200),
        default="",
        nullable=True,
        unique=False,
    )
    json = db.Column(JSONB)

    def __init__(self, data: dict):
        data = data.copy()
        if not isinstance(data, dict):
            raise Exception(f"{type(data)} {data=} has to be a dict")

        self.title = data.pop("title")
        self.href = data.pop("href")
        self.href_user = data.pop("href_user")

        self.private = data.pop("private")
        frequency = data.pop("frequency")
        if frequency in FREQUENCIES:
            self.frequency = frequency
        else:
            raise Exception(f"Frequency {frequency} is not in {FREQUENCIES}")
        self.notes = data.pop("notes")
        self.json = data.pop("json")

        if data:
            raise Exception(f"Dict {data} has extra data")

    def as_dict(self) -> dict:
        return {
            "_id": self._id,
            "title": self.title,
            "href": self.href,
            "href_user": self.href_user,
            "private": self.private,
            "frequency": self.frequency,
            "notes": self.notes,
            "json": self.json,
        }

    def __str__(self):
        return str(self.as_dict())

    def requires_update(self):
        if self.frequency == "never":
            return False

        if not self._delayed:
            return True
        elif self._delayed <= datetime.now():
            return True

        return False

    ##########################
    # FEED PARSING LOGIC BELOW
    ##########################

    def parse_list(self, results: List[Dict]):
        return results

    @staticmethod
    def process_parsing(feed_id, store_new=True, proxy=False):
        # Preparing
        new_items = []
        feed = (
            db.session.query(Feed)
            .filter_by(
                _id=feed_id,
            )
            .first()
        )
        feed_len = (
            db.session.query(Update)
            .filter_by(
                feed_id=feed_id,
            )
            .count()
        )

        # Processing
        feed_updates = feed.parse_href(
            proxy=proxy,
        )

        # Finishing with results
        if store_new:
            for each in feed_updates:
                if (
                    db.session.query(Update)
                    .filter_by(
                        feed_id=feed_id,
                        href=each["href"],
                    )
                    .count()
                    == 0
                ):
                    new_update = Update(each)
                    if new_update.filter_skip(json=feed.json):
                        continue
                    if feed_len != 0:
                        new_update.datetime = datetime.now()
                        new_update.send_telegram()
                    db.session.add(new_update)
                new_items.append(each)
            feed._delayed = datetime.now() + relativedelta(
                **{
                    feed.frequency: random.randint(1, 10),
                }
            )
            db.session.add(feed)
            db.session.commit()
        else:
            new_items = feed_updates.copy()

        # Return data
        return {
            "len": len(new_items),
            "items": new_items,
            "feed": feed,
        }

    @staticmethod
    def process_parsing_multi(force_all=False, store_new=True, proxy=False):
        results = 0
        feed_todo_ids = []
        feed_list = db.session.query(Feed).all()
        random.shuffle(feed_list)

        for feed in feed_list:
            if feed.frequency not in FREQUENCIES:
                raise ValueError(f"Invalid {feed.frequency=}, {feed.as_dict()=}")
            elif force_all or feed.requires_update():
                feed_todo_ids.append(feed._id)

        for feed_id in feed_todo_ids:
            results += Feed.process_parsing(
                feed_id=feed_id,
                store_new=store_new,
                proxy=proxy,
            )["len"]

        # with Executor() as executor:
        #     executor = executor.map(
        #         Feed.process_parsing,
        #         feed_todo_ids,
        #         [store_new]*len(feed_todo_ids),
        #         [proxy]*len(feed_todo_ids),
        #     )
        #     if options['logBar']:
        #         executor = tqdm(executor, total=len(parse_feeds))

        #     for result in executor:
        #         print(result['len'])
        #         if options['logEach'] or (options["logEmpty"] and
        # result['amount_total'] == 0):
        #             Command.print_feed(
        #                 title=result['title'],
        #                 amount=result['amount'],
        #                 time=result['time']
        #             )

        #         if options['log']:
        #             total_items += result['amount']

        return results

    @staticmethod
    def process_parsing_queue(force_all=False, store_new=True, proxy=False):
        feed_list = db.session.query(Feed).all()
        if not force_all:
            feed_list = filter(lambda x: x.requires_update(), feed_list)
        random.shuffle(feed_list)

        for feed in feed_list:
            params = pika.URLParameters(os.environ["RABBITMQ_CONNECTION_STRING"])
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            channel.basic_publish(
                exchange="swamp",
                routing_key="feed.parser",
                body=json.dumps(feed.as_dict()),
            )

    def parse_href(self, href=None, proxy: bool = True, **kwargs: Dict):
        ###############################
        #  PREPARING REQUIRED VARIABLES
        ###############################

        results = []
        if href is None:
            href = self.href

        # avoiding blocks
        referer_domain = "".join(random.choices(string.ascii_letters, k=16))
        headers = {
            # 'user-agent': feed.UserAgent_random().strip(),
            "referer": f"https://www.{ referer_domain }.com/?q={ href }"
        }
        proxyDict = {}
        if proxy and isinstance(proxy, str):
            proxyDict["http"] = "http://" + proxy
            proxyDict["https"] = "https://" + proxy

        #########################
        # STARTING DATA INGESTION
        #########################

        # using it as first if for now
        if False:
            return "NOPE"

        # rss-bridge instagram import converter
        elif 'instagram.com' in href and not kwargs.get("processed"):
            RSS_BRIDGE_URL = "http://192.168.0.155:31000"
            RSS_BRIDGE_ARGS = "action=display&bridge=InstagramBridge&context=Username&media_type=all"

            timeout = 24*60*60  # 24 hours
            username = href[26:-1]

            href = f"{RSS_BRIDGE_URL}/?{RSS_BRIDGE_ARGS}&u={username}&_cache_timeout={timeout}&format=Atom"

            results = self.parse_href(
                href=href,
                proxy=proxy,
                processed=True,
            )
            # safeguard against failed attempts
            if len(results) == 1 and "Bridge returned error 401" in results[0]['name']:
                results = []

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
        #     server = random.choice(caching_servers)
        #     self.href = f"{ server }/{ self.href[20:] }/rss"

        #     try:
        #         results = self.parse_href(proxy)
        #     except:
        #         return []

        #     base_domain = 'twitter.com'
        #     for each in results:
        #         each['href'] = each['href'].replace('#m', '')
        #         each['href'] = each['href'].replace('http://', 'https://')

        #         href_split = each['href'].split('/')
        #         href_split[2] = base_domain

        #         each['href'] = '/'.join(href_split)

        # custom tiktok import
        elif "https://www.tiktok.com/@" in href:
            href_base = "https://proxitok.pabloferreiro.es"
            href = f"{href_base}/@{ href.split('@')[-1] }/rss"

            results = self.parse_href(
                href=href,
                proxy=proxy,
            )

            results.reverse()
            for each in results:
                each["href"] = each["href"].replace(
                    "proxitok.pabloferreiro.es", "tiktok.com"
                )

        # custom RSS YouTube converter
        elif "https://www.youtube.com/channel/" in href:
            # 32 = len('https://www.youtube.com/channel/')
            # 7 = len('/videos')
            href_base = "https://www.youtube.com/feeds/videos.xml"
            href = f"{href_base}?channel_id={href[32:-7]}"

            results = self.parse_href(
                href=href,
                proxy=proxy,
            )

        # custom RSS readmanga converter
        elif "http://readmanga.live/" in href and href.find("/rss/") == -1:
            # 22 = len('http://readmanga.live/')
            name = href[22:]
            href = "feed://readmanga.live/rss/manga?name=" + name

            results = self.parse_href(
                href=href,
                proxy=proxy,
            )

            for each in results:
                split = each["href"].split("/")
                split[-3] = name
                each["href"] = "/".join(split)

        # custom RSS mintmanga converter
        elif (
            "mintmanga.com" in href
            and "mintmanga.com/rss/manga" not in href
            and not kwargs.get("processed")
        ):
            # 21 = len('http://mintmanga.com/')
            name = href[21:]
            href = "feed://mintmanga.com/rss/manga?name=" + name

            results = self.parse_href(
                href=href,
                proxy=proxy,
                processed=True,
            )

            for each in results:
                split = each["href"].split("/")
                split[-3] = name
                each["href"] = "/".join(split)

        # custom RSS deviantart converter
        elif "deviantart.com" in href and not kwargs.get("processed"):
            # 27 = len('https://www.deviantart.com/')
            # 9 = len('/gallery/')
            href = href[27:-9]
            href_base = "https://backend.deviantart.com/rss.xml?type=deviation"
            href = f"{href_base}&q=by%3A{ href }+sort%3Atime+meta%3Aall"

            results = self.parse_href(
                href=href,
                proxy=proxy,
                processed=True,
            )

        # custom onlyfans import
        elif "onlyfans.com" in href:
            # TODO
            return []

        # custom patreon import
        elif "patreon.com" in href:
            # TODO
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
        #             'href':     'https://www.lightnovelpub.com' \
        #                   + each.find('a')['href'],
        #             'datetime': datetime.strptime(
        #    each.find('time')['datetime'], '%Y-%m-%d %H:%M'),
        #             'feed_id':  self.id,
        #         })

        # default RSS import
        else:
            try:
                request = feedparser.parse(href, request_headers=headers)
            except urllib.error.URLError:
                proxyDict = urllib.request.ProxyHandler(proxyDict)

                ssl._create_default_https_context = getattr(
                    ssl, "_create_unverified_context"
                )
                request = feedparser.parse(
                    href,
                    request_headers=headers,
                    handlers=[proxyDict],
                )

            for each in request["items"]:
                if not each:
                    status = "Lagging" if self.requires_update() else "Updated"
                    message = f"{status} feed {self=} is empty, skipping"
                    capture_message(message)
                    continue
                try:
                    result_href = each["links"][0]["href"]
                except KeyError:
                    capture_message(f"Data missing URL, skipping item {self=} {each=}")
                    continue

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
                    "PDT": tz.gettz("America/Los_Angeles"),
                    "PST": tz.gettz("America/Juneau"),
                }
                if result_datetime.isdigit():
                    result_datetime = datetime.utcfromtimestamp(int(result_datetime))
                elif not isinstance(result_datetime, datetime):
                    result_datetime = parser.parse(
                        result_datetime,
                        tzinfos=tzinfos,
                    )

                if each.get("title_detail"):
                    result_name = each["title_detail"]["value"]
                else:
                    result_name = ""

                # APPEND RESULT
                results.append(
                    {
                        "name": result_name,
                        "href": result_href,
                        "datetime": result_datetime,
                        "feed_id": self._id,
                    }
                )

        return self.parse_list(results=results)
