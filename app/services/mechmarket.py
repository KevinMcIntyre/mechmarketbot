import requests
import pytz
from datetime import datetime, timezone, timedelta


class MechMarket:
    def __init__(self):
        # use the db to update most_recent_post_date
        self.previous_refresh = None
        self.most_recent_refresh = datetime.now(timezone.utc).replace(tzinfo=pytz.UTC) - timedelta(minutes=2)
        self.__url__ = "http://www.reddit.com/r/mechmarket/new.json?sort=new&count=20"
        self.posts = []

    def refresh_posts(self):
        response = requests.get(self.__url__, headers={'User-agent': 'MechMarketBot', 'Connection': 'close'})

        if response.ok:
            self.previous_refresh = self.most_recent_refresh
            self.most_recent_refresh = datetime.now(timezone.utc).replace(tzinfo=pytz.UTC)
            self.posts = response.json()['data']['children']
        else:
            self.posts = []
            print("Request  with status {}".format(response.status_code))
            raise RuntimeError("Failed request")

    def get_all_posts(self):
        return self.posts

    def get_selling_posts(self):
        return self.get_posts_by_type('selling')

    def get_buying_posts(self):
        return self.get_posts_by_type('buying')

    def get_group_buy_posts(self):
        return self.get_posts_by_type('groupbuy')

    def get_vendor_posts(self):
        return self.get_posts_by_type('vendor')

    def get_artisan_posts(self):
        return self.get_posts_by_type('artisan')

    def get_posts_by_type(self, post_type):
        return [post for post in self.posts if (post_type == self.derive_post_type(post['data']) and
                                                datetime.utcfromtimestamp(int(post['data']['created_utc'])).replace(
                                                    tzinfo=pytz.UTC) > self.previous_refresh)]

    def derive_post_type(self, post):
        post_type = self.derive_post_type_by_flair(post['link_flair_text'])
        if post_type is None:
            return self.derive_post_type_by_title(post['title'])
        return post_type

    def derive_post_type_by_flair(self, flair):
        if flair is not None and flair is not '':
            return "".join(flair.lower())
        else:
            return None

    def derive_post_type_by_title(self, title):
        split_post = title.upper().split('[W]')
        if len(split_post) > 1 and 'PAYPAL' in split_post[1]:
            return 'buying'
        else:
            post_title = "".join(title.upper().split())
            if '[H]PAYPAL' not in post_title:
                return 'selling'
            elif '[GB]' in post_title:
                return 'groupbuy'
            elif '[VENDOR]' in post_title:
                return 'vendor'
            elif '[ARTISAN]' in post_title:
                return 'artisan'
            else:
                return None
