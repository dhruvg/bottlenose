import hmac
import os
import time

from base64 import b64encode
from hashlib import sha256
from urllib import parse

from bottlenose import Call
from bottlenose.api import quote_query


SERVICE_DOMAINS = {
    'CA': ('webservices.amazon.ca', 'xml-ca.amznxslt.com'),
    'CN': ('webservices.amazon.cn', 'xml-cn.amznxslt.com'),
    'DE': ('webservices.amazon.de', 'xml-de.amznxslt.com'),
    'ES': ('webservices.amazon.es', 'xml-es.amznxslt.com'),
    'FR': ('webservices.amazon.fr', 'xml-fr.amznxslt.com'),
    'IN': ('webservices.amazon.in', 'xml-in.amznxslt.com'),
    'IT': ('webservices.amazon.it', 'xml-it.amznxslt.com'),
    'JP': ('webservices.amazon.co.jp', 'xml-jp.amznxslt.com'),
    'UK': ('webservices.amazon.co.uk', 'xml-uk.amznxslt.com'),
    'US': ('webservices.amazon.com', 'xml-us.amznxslt.com'),
    'BR': ('webservices.amazon.com.br', 'xml-br.amznxslt.com'),
    'MX': ('webservices.amazon.com.mx', 'xml-mx.amznxslt.com')
}


class AmazonError(Exception):
    pass


class AmazonCall(Call):
    """
    A call to the Amazon Product Advertising API.
    """
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 associate_tag=None, version="2013-08-01", region=None,
                 operation=None, timeout=None, max_qps=None, parser=None,
                 cache_reader=None, cache_writer=None,
                 error_handler=None, max_retries=5, last_query_time=None):
        super(AmazonCall, self).__init__(operation, timeout, max_qps, parser,
                                         cache_reader, cache_writer,
                                         error_handler, max_retries,
                                         last_query_time)

        self.aws_access_key_id = (aws_access_key_id or
                                  os.environ.get('AWS_ACCESS_KEY_ID'))
        self.aws_secret_access_key = (aws_secret_access_key or
                                      os.environ.get('AWS_SECRET_ACCESS_KEY'))
        self.associate_tag = (associate_tag or
                              os.environ.get('AWS_ASSOCIATE_TAG'))
        self.version = version
        self.region = region

    def __getattr__(self, k):
        try:
            return super(AmazonCall, self).__getattr__(self, k)
        except:
            return AmazonCall(self.aws_access_key_id, self.aws_secret_access_key,
                              self.associate_tag,
                              version=self.version, region=self.region,
                              operation=k, timeout=self.timeout,
                              max_qps=self.max_qps, parser=self.parser,
                              cache_reader=self.cache_reader,
                              cache_writer=self.cache_writer,
                              error_handler=self.error_handler,
                              max_retries=self.max_retries,
                              last_query_time=self._last_query_time)

    def api_url(self, **kwargs):
        """The URL for making the given query against the API."""
        query = {
            'Operation': self.operation,
            'Service': "AWSECommerceService",
            'Timestamp': time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            'Version': self.version,
        }
        query.update(kwargs)

        query['AWSAccessKeyId'] = self.aws_access_key_id
        query['Timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                           time.gmtime())

        if self.associate_tag:
            query['AssociateTag'] = self.associate_tag

        service_domain = SERVICE_DOMAINS[self.region][0]
        quoted_strings = quote_query(query)

        data = "GET\n" + service_domain + "\n/onca/xml\n" + quoted_strings

        # convert unicode to UTF8 bytes for hmac library
        if type(self.aws_secret_access_key) is str:
            self.aws_secret_access_key = self.aws_secret_access_key.encode('utf-8')

        if type(data) is str:
            data = data.encode('utf-8')

        # calculate sha256 signature
        digest = hmac.new(self.aws_secret_access_key, data, sha256).digest()

        # base64 encode and urlencode
        signature = parse.quote(b64encode(digest))

        return ("https://" + service_domain + "/onca/xml?" +
                quoted_strings + "&Signature=%s" % signature)

    def cache_url(self, **kwargs):
        """A simplified URL to be used for caching the given query."""
        query = {
            'Operation': self.operation,
            'Service': "AWSECommerceService",
            'Version': self.version,
        }
        query.update(kwargs)

        service_domain = SERVICE_DOMAINS[self.region][0]

        return "https://" + service_domain + "/onca/xml?" + quote_query(query)

    def __call__(self, **kwargs):
        if 'Style' in kwargs:
            raise AmazonError("The `Style` parameter has been discontinued by"
                              " AWS. Please remove all references to it and"
                              " reattempt your request.")
        return super(AmazonCall, self).__call__(**kwargs)


class Amazon(AmazonCall):
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 associate_tag=None, version="2013-08-01", region="US",
                 operation=None, timeout=None, max_qps=None, parser=None,
                 cache_reader=None, cache_writer=None, error_handler=None,
                 max_retries=5):
        """
        Create an Amazon API object.

        aws_access_key_id: Your AWS Access Key, sent with API queries. If not
                           set, will be automatically read from the environment
                           variable $AWS_ACCESS_KEY_ID
        aws_secret_access_key: Your AWS Secret Key, used to sign API queries. If
                               not set, will be automatically read from the
                               environment variable $AWS_SECRET_ACCESS_KEY
        associate_tag: Your "username" for the Amazon Affiliate program,
                       sent with API queries.
        version: API version. The default should work.
        region: ccTLD you want to search for products on (e.g. 'UK'
                for amazon.co.uk). Must be uppercase. Default is 'US'.
        """
        AmazonCall.__init__(self, aws_access_key_id, aws_secret_access_key,
                            associate_tag, version=version,
                            region=region, operation=operation, timeout=timeout,
                            max_qps=max_qps, parser=parser,
                            cache_reader=cache_reader,
                            cache_writer=cache_writer,
                            error_handler=error_handler,
                            max_retries=max_retries)


__all__ = ["Amazon", "AmazonError"]
