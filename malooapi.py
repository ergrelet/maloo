# coding: utf8

"""
malooapi.py
--------

Here's the definition of the MalooApi class.
"""

import copy
import json
import urllib.parse
import urllib.request

import twitter

class MalooApi:
    """
    TODO
    """
    def __init__(self, config):
        self.config = copy.copy(config)

    def find_on_googleimage(self, query):
        """ Retrieve the first image's URL on Google Images by searching
        for 'query'
        Note: You need to edit your config.ini to setup the API """
        url = "https://www.googleapis.com/customsearch/v1" \
                + "?q={}".format(urllib.parse.quote_plus(query)) \
                + "&searchType=image" \
                + "&key={}".format(self.config["customsearch_key"]) \
                + "&cx={}".format(self.config["customsearch_id"])
                # &fileType=jpg
        try:
            response = urllib.request.urlopen(url, timeout=5)
        except urllib.error.HTTPError as ex:
            raise ex
        data = response.read().decode("utf-8")
        result = json.loads(data)

        # Find an image that is accessible
        nb_of_images = len(result['items'])
        for i in range(nb_of_images):
            image_url = result['items'][i]['link']
            try:
                urllib.request.urlopen(image_url, timeout=5)
            except urllib.error.HTTPError as ex:
                continue
            break

        return image_url

    def upload_to_imgur(self, bin_input):
        """ Uploads an image to imgur
        Note: You need to edit your config.ini to setup the API """
        api_url = "https://api.imgur.com/3/image.json"
        api_key = self.config["imgur_key"]

        binary_data = bin_input.getvalue()
        payload = {'image': binary_data, 'type': 'file'}
        details = urllib.parse.urlencode(payload).encode('ascii')
        url = urllib.request.Request(api_url, details)
        url.add_header("Authorization", "Client-ID {}".format(api_key))
        try:
            response = urllib.request.urlopen(url, timeout=20).read().decode('utf8', 'ignore')
        except Exception as ex:
            raise ex
        j = json.loads(response)

        return j['data']['link']

    def post_on_tweet(self, message):
        """ Posts 'message" on twitter.
        Note: You need to edit your config.ini to setup the API """
        # Twitter
        try:
            oauth = twitter.OAuth(self.config["twitter_token"], \
                                            self.config["twitter_token_secret"], \
                                            self.config["twitter_key"], \
                                            self.config["twitter_secret"])
            client = twitter.Twitter(auth=oauth)
            client.statuses.update(status=message)
        except Exception:
            pass
