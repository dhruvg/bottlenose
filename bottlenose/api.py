# Copyright 2012 Lionheart Software LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import gzip
import logging
import random
import sys
import time

from urllib import parse, request


log = logging.getLogger(__name__)


def quote_query(query):
    """Turn a dictionary into a query string in a URL, with keys in alphabetical order."""
    return "&".join("%s=%s" % (
        k, parse.quote(
            str(query[k]).encode('utf-8'), safe='~'))
            for k in sorted(query))


class Call(object):
    def __init__(self, operation=None, timeout=None, max_qps=None,
                 parser=None, cache_reader=None, cache_writer=None,
                 error_handler=None, max_retries=5, last_query_time=None):
        """
        operation: optional API operation.
        timeout: optional timeout for queries
        max_qps: optional maximum queries per second. If we've made an API call
                 on this object more recently that 1/MaxQPS, we'll wait
                 before making the call. Useful for making batches of queries.
                 You generally want to set this a little lower than the
                 max (so 0.9, not 1.0).
        parser: a function that takes the raw API response (XML in a
                bytestring) and returns a more convenient object of
                your choice; if set, API calls will pass the response through
                this
        cache_reader: Called before attempting to make an API call.
                      A function that takes a single argument, the URL that
                      would be passed to the API, minus auth information,
                      and returns a cached version of the (unparsed) response,
                      or None
        cache_writer: Called after a successful API call. A function that
                      takes two arguments, the same URL passed to
                      CacheReader, and the (unparsed) API response.
        error_handler: Called after an unsuccessful API call, with a
                       dictionary containing these values:
                           exception: the exception (an HTTPError or URLError)
                           api_url: the url called
                           cache_url: the url used for caching purposes
                                      (see CacheReader above)
                       If this returns true, the call will be retried
                       (you generally want to wait some time before
                       returning, in this case)
        max_retries: Max retries.
        last_query_time: Last query timestamp.
        """

        self.operation = operation
        self.cache_reader = cache_reader
        self.cache_writer = cache_writer
        self.error_handler = error_handler
        self.max_qps = max_qps
        self.parser = parser
        self.timeout = timeout
        self.max_retries = max_retries

        # put this in a list so it can be shared between instances
        self._last_query_time = last_query_time or [None]

    def api_url(self, **kwargs):
        raise NotImplementedError

    def cache_url(self, **kwargs):
        raise NotImplementedError

    def _maybe_parse(self, response_text):
        if self.parser:
            return self.parser(response_text)
        else:
            return response_text

    def _call_api(self, api_url, err_env):
        """
        urlopen(), plus error handling and possible retries.

        err_env is a dict of additional info passed to the error handler
        """
        attempt = 0
        while True:  # may retry on error
            attempt += 1
            api_request = request.Request(
                api_url, headers={"Accept-Encoding": "gzip",
                                  "User-Agent": random_desktop_user_agent()})

            log.debug("API URL: %s" % api_url)

            try:
                # the simple way
                return request.urlopen(api_request, timeout=self.timeout)
            except:
                if not self.error_handler or attempt > self.max_retries:
                    raise

                exception = sys.exc_info()[1]
                err = {'exception': exception}
                err.update(err_env)
                if not self.error_handler(err):
                    raise

    def __call__(self, **kwargs):
        cache_url = self.cache_url(**kwargs)

        if self.cache_reader:
            cached_response_text = self.cache_reader(cache_url)
            if cached_response_text is not None:
                return self._maybe_parse(cached_response_text)

        api_url = self.api_url(**kwargs)

        # throttle ourselves if need be
        if self.max_qps:
            last_query_time = self._last_query_time[0]
            if last_query_time:
                wait_time = 1 / self.max_qps - (time.time() - last_query_time)
                if wait_time > 0:
                    log.debug('Waiting %.3fs to call API' % wait_time)
                    time.sleep(wait_time)

            self._last_query_time[0] = time.time()

        # make the actual API call
        response = self._call_api(api_url, {'api_url': api_url, 'cache_url': cache_url})

        # decompress the response if need be
        content_encoding = response.info().get("Content-Encoding")
        if content_encoding and "gzip" in content_encoding:
            response_text = gzip.decompress(response.read())
        else:
            response_text = response.read()

        # write it back to the cache
        if self.cache_writer:
            self.cache_writer(cache_url, response_text)

        # parse and return it
        return self._maybe_parse(response_text)


def random_desktop_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:16.0) Gecko/20100101 Firefox/16.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/536.26.17 (KHTML, like Gecko) Version/6.0.2 Safari/536.26.17',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 5.1; rv:13.0) Gecko/20100101 Firefox/13.0.1',
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; FunWebProducts; .NET CLR 1.1.4322; PeoplePal 6.2)',
        'Mozilla/5.0 (Windows NT 5.1; rv:5.0.1) Gecko/20100101 Firefox/5.0.1',
        'Mozilla/5.0 (Windows NT 6.0) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/13.0.782.112 Safari/535.1',
        'Opera/9.80 (Windows NT 5.1; U; en) Presto/2.10.289 Version/12.01',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.95 Safari/537.11',
        'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)',
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1) )',
        'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727)',
        'Mozilla/5.0 (Windows NT 6.1; rv:2.0b7pre) Gecko/20100921 Firefox/4.0b7pre',
        'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322)',
        'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.95 Safari/537.11',
        'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1) ; .NET CLR 3.5.30729)',
        'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.95 Safari/537.11',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/13.0.782.112 Safari/535.1',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Mozilla/4.0 (compatible; MSIE 6.0; MSIE 5.5; Windows NT 5.0) Opera 7.02 Bork-edition [en]',
        'Mozilla/5.0 (Windows NT 6.1; rv:5.0) Gecko/20100101 Firefox/5.02',
        'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:5.0) Gecko/20100101 Firefox/5.0',
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; MRA 5.8 (build 4157); .NET CLR 2.0.50727; AskTbPTV/5.11.3.15590)',
        'Mozilla/5.0 (Windows NT 5.1; rv:16.0) Gecko/20100101 Firefox/16.0',
        'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:17.0) Gecko/20100101 Firefox/17.0',
        'Mozilla/5.0 (Windows NT 6.1; rv:16.0) Gecko/20100101 Firefox/16.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.57.2 (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.91 Safari/537.11',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/536.26.17 (KHTML, like Gecko) Version/6.0.2 Safari/536.26.17',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:16.0) Gecko/20100101 Firefox/16.0',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:17.0) Gecko/17.0 Firefox/17.0',
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; TencentTraveler ; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1) ; .NET CLR 2.0.50727)',
        'Mozilla/5.0 (iPad; CPU OS 6_0_1 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A523 Safari/8536.25',
        'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:16.0) Gecko/20100101 Firefox/16.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.95 Safari/537.11',
        'Mozilla/5.0 (Windows NT 5.1; rv:17.0) Gecko/20100101 Firefox/17.0',
        'Mozilla/5.0 (Windows NT 5.1; rv:17.0) Gecko/20100101 Firefox/17.0'
    ]
    return random.choice(user_agents)
