from bottlenose import Call, quote_query


GOODREADS_DOMAIN = "www.goodreads.com"


class GoodreadsCall(Call):
    """
    A call to the Goodreads API.
    """
    def __init__(self, goodreads_api_key=None, operation=None,
                 timeout=None, max_qps=None, parser=None,
                 cache_reader=None, cache_writer=None,
                 error_handler=None, max_retries=5, last_query_time=None):
        super(GoodreadsCall, self).__init__(operation, timeout, max_qps, parser,
                                            cache_reader, cache_writer,
                                            error_handler, max_retries, last_query_time)

        self.goodreads_api_key = goodreads_api_key

    def __getattr__(self, k):
        try:
            return super(GoodreadsCall, self).__getattr__(self, k)
        except:
            return GoodreadsCall(self.goodreads_api_key,
                                 operation=k, timeout=self.timeout,
                                 max_qps=self.max_qps, parser=self.parser,
                                 cache_reader=self.cache_reader,
                                 cache_writer=self.cache_writer,
                                 error_handler=self.error_handler,
                                 max_retries=self.max_retries,
                                 last_query_time=self._last_query_time)

    def api_url(self, **kwargs):
        """The URL for making the given query against the API."""
        query = kwargs
        quoted_strings = quote_query(query)

        return ("https://" + GOODREADS_DOMAIN + "/" + self.operation +
                "/index.xml?" + quoted_strings + "&key=%s" % self.goodreads_api_key)

    def cache_url(self, **kwargs):
        """A simplified URL to be used for caching the given query."""
        query = kwargs
        quoted_strings = quote_query(query)

        return ("https://" + GOODREADS_DOMAIN + "/" + self.operation +
                "/index.xml?" + quoted_strings)


class Goodreads(GoodreadsCall):
    def __init__(self, goodreads_api_key=None, operation=None,
                 timeout=None, max_qps=None, parser=None,
                 cache_reader=None, cache_writer=None, error_handler=None,
                 max_retries=5):
        """
        Create an Goodreads API object.

        goodreads_api_key: Your Goodreads API Key, sent with API queries.
        """
        GoodreadsCall.__init__(self, goodreads_api_key, operation=operation,
                               timeout=timeout, max_qps=max_qps, parser=parser,
                               cache_reader=cache_reader, cache_writer=cache_writer,
                               error_handler=error_handler, max_retries=max_retries)

__all__ = ["Goodreads"]
