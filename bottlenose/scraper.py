from bottlenose import Call


class ScraperCall(Call):
    """
    A call to any arbitrary URL.
    """
    def __init__(self, operation=None, timeout=None, max_qps=None,
                 parser=None, cache_reader=None, cache_writer=None,
                 error_handler=None, max_retries=5, last_query_time=None):
        super(ScraperCall, self).__init__(operation, timeout, max_qps, parser,
                                          cache_reader, cache_writer,
                                          error_handler, max_retries, last_query_time)

    def __getattr__(self, k):
        try:
            return super(ScraperCall, self).__getattr__(self, k)
        except:
            return ScraperCall(operation=k, timeout=self.timeout,
                               max_qps=self.max_qps, parser=self.parser,
                               cache_reader=self.cache_reader,
                               cache_writer=self.cache_writer,
                               error_handler=self.error_handler,
                               max_retries=self.max_retries,
                               last_query_time=self._last_query_time)

    def api_url(self, **kwargs):
        """The URL for making the given query against the API."""
        return kwargs.get('url')

    def cache_url(self, **kwargs):
        """A simplified URL to be used for caching the given query."""
        return self.api_url(**kwargs)


class Scraper(ScraperCall):
    def __init__(self, operation=None, timeout=None, max_qps=None, parser=None,
                 cache_reader=None, cache_writer=None, error_handler=None,
                 max_retries=5):
        """
        Create a Scraper object.
        """
        ScraperCall.__init__(self, operation=operation,
                             timeout=timeout, max_qps=max_qps, parser=parser,
                             cache_reader=cache_reader, cache_writer=cache_writer,
                             error_handler=error_handler, max_retries=max_retries)

__all__ = ["Scraper"]
