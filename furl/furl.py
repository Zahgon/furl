# -*- coding: utf-8 -*-

#
# furl - URL manipulation made simple.
#
# Ansgar Grunseid
# grunseid.com
# grunseid@gmail.com
#
# License: Build Amazing Things (Unlicense)
#

import re
import abc
import warnings
from copy import deepcopy
from posixpath import normpath

import six
from six.moves import urllib
from six.moves.urllib.parse import quote, unquote
try:
    from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
    ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from .omdict1D import omdict1D
from .compat import string_types, UnicodeMixin
from .common import (
    callable_attr, is_iterable_but_not_string, absent as _absent)


# Map of common protocols, as suggested by the common protocols included in
# urllib/parse.py, to their default ports. Protocol scheme strings are
# lowercase.
#
# TODO(Ans): Is there a public map of schemes to their default ports? If not,
# create one? Best I (Ansgar) could find is
#
#   https://gist.github.com/mahmoud/2fe281a8daaff26cfe9c15d2c5bf5c8b
#
DEFAULT_PORTS = {
    'acap': 674,
    'afp': 548,
    'dict': 2628,
    'dns': 53,
    'ftp': 21,
    'git': 9418,
    'gopher': 70,
    'hdl': 2641,
    'http': 80,
    'https': 443,
    'imap': 143,
    'ipp': 631,
    'ipps': 631,
    'irc': 194,
    'ircs': 6697,
    'ldap': 389,
    'ldaps': 636,
    'mms': 1755,
    'msrp': 2855,
    'mtqp': 1038,
    'nfs': 111,
    'nntp': 119,
    'nntps': 563,
    'pop': 110,
    'prospero': 1525,
    'redis': 6379,
    'rsync': 873,
    'rtsp': 554,
    'rtsps': 322,
    'rtspu': 5005,
    'sftp': 22,
    'sip': 5060,
    'sips': 5061,
    'smb': 445,
    'snews': 563,
    'snmp': 161,
    'ssh': 22,
    'svn': 3690,
    'telnet': 23,
    'tftp': 69,
    'ventrilo': 3784,
    'vnc': 5900,
    'wais': 210,
    'ws': 80,
    'wss': 443,
    'xmpp': 5222,
}


def lget(lst, index, default=None):
    pass


def attemptstr(o):
    pass


def utf8(o, default=_absent):
    pass


def non_string_iterable(o):
    pass


# TODO(grun): Support IDNA2008 via the third party idna module. See
# https://github.com/gruns/furl/issues/73#issuecomment-226549755.
def idna_encode(o):
    pass


def idna_decode(o):
    pass


def is_valid_port(port):
    pass


def static_vars(**kwargs):
    def decorator(func):
        pass
    return decorator


def create_quote_fn(safe_charset, quote_plus):
    pass


#
# TODO(grun): Update some of the regex functions below to reflect the fact that
# the valid encoding of Path segments differs slightly from the valid encoding
# of Fragment Path segments. Similarly, the valid encodings of Query keys and
# values differ slightly from the valid encodings of Fragment Query keys and
# values.
#
# For example, '?' and '#' don't need to be encoded in Fragment Path segments
# but they must be encoded in Path segments. Similarly, '#' doesn't need to be
# encoded in Fragment Query keys and values, but must be encoded in Query keys
# and values.
#
# Perhaps merge them with URLPath, FragmentPath, URLQuery, and
# FragmentQuery when those new classes are created (see the TODO
# currently at the top of the source, 02/03/2012).
#

# RFC 3986 (https://www.ietf.org/rfc/rfc3986.txt)
#
#   unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
#
#   pct-encoded = "%" HEXDIG HEXDIG
#
#   sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
#                 / "*" / "+" / "," / ";" / "="
#
#   pchar       = unreserved / pct-encoded / sub-delims / ":" / "@"
#
#   === Path ===
#   segment     = *pchar
#
#   === Query ===
#   query       = *( pchar / "/" / "?" )
#
#   === Scheme ===
#   scheme      = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
#
PERCENT_REGEX = r'\%[a-fA-F\d][a-fA-F\d]'
INVALID_HOST_CHARS = '!@#$%^&\'\"*()+=:;/'


@static_vars(regex=re.compile(
    r'^([\w%s]|(%s))*$' % (re.escape('-.~:@!$&\'()*+,;='), PERCENT_REGEX)))
def is_valid_encoded_path_segment(segment):
    pass


@static_vars(regex=re.compile(
    r'^([\w%s]|(%s))*$' % (re.escape('-.~:@!$&\'()*+,;/?'), PERCENT_REGEX)))
def is_valid_encoded_query_key(key):
    pass


@static_vars(regex=re.compile(
    r'^([\w%s]|(%s))*$' % (re.escape('-.~:@!$&\'()*+,;/?='), PERCENT_REGEX)))
def is_valid_encoded_query_value(value):
    pass


@static_vars(regex=re.compile(r'[a-zA-Z][a-zA-Z\-\.\+]*'))
def is_valid_scheme(scheme):
    return is_valid_scheme.regex.match(scheme) is not None


@static_vars(regex=re.compile('[%s]' % re.escape(INVALID_HOST_CHARS)))
def is_valid_host(hostname):
    pass


def get_scheme(url):
    if url.startswith(':'):
        return ''

    # Avoid incorrect scheme extraction with url.find(':') when other URL
    # components, like the path, query, fragment, etc, may have a colon in
    # them. For example, the URL 'a?query:', whose query has a ':' in it.
    no_fragment = url.split('#', 1)[0]
    no_query = no_fragment.split('?', 1)[0]
    no_path_or_netloc = no_query.split('/', 1)[0]
    scheme = url[:max(0, no_path_or_netloc.find(':'))] or None

    if scheme is not None and not is_valid_scheme(scheme):
        return None

    return scheme


def strip_scheme(url):
    scheme = get_scheme(url) or ''
    url = url[len(scheme):]
    if url.startswith(':'):
        url = url[1:]
    return url


def set_scheme(url, scheme):
    after_scheme = strip_scheme(url)
    if scheme is None:
        return after_scheme
    else:
        return '%s:%s' % (scheme, after_scheme)


# 'netloc' in Python parlance, 'authority' in RFC 3986 parlance.
def has_netloc(url):
    pass


def urlsplit(url):
    """
    Parameters:
      url: URL string to split.
    Returns: urlparse.SplitResult tuple subclass, just like
      urlparse.urlsplit() returns, with fields (scheme, netloc, path,
      query, fragment, username, password, hostname, port). See
        http://docs.python.org/library/urlparse.html#urlparse.urlsplit
      for more details on urlsplit().
    """
    original_scheme = get_scheme(url)

    # urlsplit() parses URLs differently depending on whether or not the URL's
    # scheme is in any of
    #
    #   urllib.parse.uses_fragment
    #   urllib.parse.uses_netloc
    #   urllib.parse.uses_params
    #   urllib.parse.uses_query
    #   urllib.parse.uses_relative
    #
    # For consistent URL parsing, switch the URL's scheme to 'http', a scheme
    # in all of the aforementioned uses_* lists, and afterwards revert to the
    # original scheme (which may or may not be in some, or all, of the the
    # uses_* lists).
    if original_scheme is not None:
        url = set_scheme(url, 'http')

    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)

    # Detect and preserve the '//' before the netloc, if present. E.g. preserve
    # URLs like 'http:', 'http://', and '///sup' correctly.
    after_scheme = strip_scheme(url)
    if after_scheme.startswith('//'):
        netloc = netloc or ''
    else:
        netloc = None

    scheme = original_scheme

    return urllib.parse.SplitResult(scheme, netloc, path, query, fragment)


def urljoin(base, url):
    """
    Parameters:
      base: Base URL to join with <url>.
      url: Relative or absolute URL to join with <base>.

    Returns: The resultant URL from joining <base> and <url>.
    """
    pass


def join_path_segments(*args):
    """
    Join multiple lists of path segments together, intelligently
    handling path segments borders to preserve intended slashes of the
    final constructed path.

    This function is not encoding aware. It doesn't test for, or change,
    the encoding of path segments it is passed.

    Examples:
      join_path_segments(['a'], ['b']) == ['a','b']
      join_path_segments(['a',''], ['b']) == ['a','b']
      join_path_segments(['a'], ['','b']) == ['a','b']
      join_path_segments(['a',''], ['','b']) == ['a','','b']
      join_path_segments(['a','b'], ['c','d']) == ['a','b','c','d']

    Returns: A list containing the joined path segments.
    """
    pass


def remove_path_segments(segments, remove):
    """
    Removes the path segments of <remove> from the end of the path
    segments <segments>.

    Examples:
      # ('/a/b/c', 'b/c') -> '/a/'
      remove_path_segments(['','a','b','c'], ['b','c']) == ['','a','']
      # ('/a/b/c', '/b/c') -> '/a'
      remove_path_segments(['','a','b','c'], ['','b','c']) == ['','a']

    Returns: The list of all remaining path segments after the segments
    in <remove> have been removed from the end of <segments>. If no
    segments from <remove> were removed from <segments>, <segments> is
    returned unmodified.
    """
    pass


def quacks_like_a_path_with_segments(obj):
    pass


class Path(object):

    """
    Represents a path comprised of zero or more path segments.

      http://tools.ietf.org/html/rfc3986#section-3.3

    Path parameters aren't supported.

    Attributes:
      _force_absolute: Function whos boolean return value specifies
        whether self.isabsolute should be forced to True or not. If
        _force_absolute(self) returns True, isabsolute is read only and
        raises an AttributeError if assigned to. If
        _force_absolute(self) returns False, isabsolute is mutable and
        can be set to True or False. URL paths use _force_absolute and
        return True if the netloc is non-empty (not equal to
        ''). Fragment paths are never read-only and their
        _force_absolute(self) always returns False.
      segments: List of zero or more path segments comprising this
        path. If the path string has a trailing '/', the last segment
        will be '' and self.isdir will be True and self.isfile will be
        False. An empty segment list represents an empty path, not '/'
        (though they have the same meaning).
      isabsolute: Boolean whether or not this is an absolute path or
        not. An absolute path starts with a '/'. self.isabsolute is
        False if the path is empty (self.segments == [] and str(path) ==
        '').
      strict: Boolean whether or not UserWarnings should be raised if
        improperly encoded path strings are provided to methods that
        take such strings, like load(), add(), set(), remove(), etc.
    """

    # From RFC 3986:
    #   segment       = *pchar
    #   pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
    #   unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
    #   sub-delims    = "!" / "$" / "&" / "'" / "(" / ")"
    #                       / "*" / "+" / "," / ";" / "="
    SAFE_SEGMENT_CHARS = ":@-._~!$&'()*+,;="

    def __init__(self, path='', force_absolute=lambda _: False, strict=False):
        self.segments = []

        self.strict = strict
        self._isabsolute = False
        self._force_absolute = force_absolute

        self.load(path)

    def load(self, path):
        """
        Load <path>, replacing any existing path. <path> can either be
        a Path instance, a list of segments, a path string to adopt.

        Returns: <self>.
        """
        pass

    def add(self, path):
        """
        Add <path> to the existing path. <path> can either be a Path instance,
        a list of segments, or a path string to append to the existing path.

        Returns: <self>.
        """
        pass

    def set(self, path):
        pass

    def remove(self, path):
        pass

    def normalize(self):
        """
        Normalize the path. Turn '//a/./b/../c//' into '/a/c/'.

        Returns: <self>.
        """
        pass

    def asdict(self):
        pass

    @property
    def isabsolute(self):
        pass

    @isabsolute.setter
    def isabsolute(self, isabsolute):
        """
        Raises: AttributeError if _force_absolute(self) returns True.
        """
        pass

    @property
    def isdir(self):
        """
        Returns: True if the path ends on a directory, False
        otherwise. If True, the last segment is '', representing the
        trailing '/' of the path.
        """
        pass

    @property
    def isfile(self):
        """
        Returns: True if the path ends on a file, False otherwise. If
        True, the last segment is not '', representing some file as the
        last segment of the path.
        """
        pass

    def __truediv__(self, path):
        copy = deepcopy(self)
        return copy.add(path)

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not self == other

    def __bool__(self):
        return len(self.segments) > 0
    __nonzero__ = __bool__

    def __str__(self):
        segments = list(self.segments)
        if self.isabsolute:
            if not segments:
                segments = ['', '']
            else:
                segments.insert(0, '')
        return self._path_from_segments(segments)

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, str(self))

    def _segments_from_path(self, path):
        """
        Returns: The list of path segments from the path string <path>.

        Raises: UserWarning if <path> is an improperly encoded path
        string and self.strict is True.

        TODO(grun): Accept both list values and string values and
        refactor the list vs string interface testing to this common
        method.
        """
        pass

    def _path_from_segments(self, segments):
        """
        Combine the provided path segments <segments> into a path string. Path
        segments in <segments> will be quoted.

        Returns: A path string with quoted path segments.
        """
        pass


@six.add_metaclass(abc.ABCMeta)
class PathCompositionInterface(object):

    """
    Abstract class interface for a parent class that contains a Path.
    """

    def __init__(self, strict=False):
        """
        Params:
          force_absolute: See Path._force_absolute.

        Assignments to <self> in __init__() must be added to
        __setattr__() below.
        """
        self._path = Path(force_absolute=self._force_absolute, strict=strict)

    @property
    def path(self):
        pass

    @property
    def pathstr(self):
        """This method is deprecated. Use str(furl.path) instead."""
        pass

    @abc.abstractmethod
    def _force_absolute(self, path):
        """
        Subclass me.
        """
        pass

    def __setattr__(self, attr, value):
        """
        Returns: True if this attribute is handled and set here, False
        otherwise.
        """
        if attr == '_path':
            self.__dict__[attr] = value
            return True
        elif attr == 'path':
            self._path.load(value)
            return True
        return False


@six.add_metaclass(abc.ABCMeta)
class URLPathCompositionInterface(PathCompositionInterface):

    """
    Abstract class interface for a parent class that contains a URL
    Path.

    A URL path's isabsolute attribute is absolute and read-only if a
    netloc is defined. A path cannot start without '/' if there's a
    netloc. For example, the URL 'http://google.coma/path' makes no
    sense. It should be 'http://google.com/a/path'.

    A URL path's isabsolute attribute is mutable if there's no
    netloc. The scheme doesn't matter. For example, the isabsolute
    attribute of the URL path in 'mailto:user@host.com', with scheme
    'mailto' and path 'user@host.com', is mutable because there is no
    netloc. See

      http://en.wikipedia.org/wiki/URI_scheme#Examples
    """

    def __init__(self, strict=False):
        PathCompositionInterface.__init__(self, strict=strict)

    def _force_absolute(self, path):
        pass


@six.add_metaclass(abc.ABCMeta)
class FragmentPathCompositionInterface(PathCompositionInterface):

    """
    Abstract class interface for a parent class that contains a Fragment
    Path.

    Fragment Paths they be set to absolute (self.isabsolute = True) or
    not absolute (self.isabsolute = False).
    """

    def __init__(self, strict=False):
        PathCompositionInterface.__init__(self, strict=strict)

    def _force_absolute(self, path):
        pass


class Query(object):

    """
    Represents a URL query comprised of zero or more unique parameters
    and their respective values.

      http://tools.ietf.org/html/rfc3986#section-3.4


    All interaction with Query.params is done with unquoted strings. So

      f.query.params['a'] = 'a%5E'

    means the intended value for 'a' is 'a%5E', not 'a^'.


    Query.params is implemented as an omdict1D object - a one
    dimensional ordered multivalue dictionary. This provides support for
    repeated URL parameters, like 'a=1&a=2'. omdict1D is a subclass of
    omdict, an ordered multivalue dictionary. Documentation for omdict
    can be found here

      https://github.com/gruns/orderedmultidict

    The one dimensional aspect of omdict1D means that a list of values
    is interpreted as multiple values, not a single value which is
    itself a list of values. This is a reasonable distinction to make
    because URL query parameters are one dimensional: query parameter
    values cannot themselves be composed of sub-values.

    So what does this mean? This means we can safely interpret

      f = furl('http://www.google.com')
      f.query.params['arg'] = ['one', 'two', 'three']

    as three different values for 'arg': 'one', 'two', and 'three',
    instead of a single value which is itself some serialization of the
    python list ['one', 'two', 'three']. Thus, the result of the above
    will be

      f.query.allitems() == [
        ('arg','one'), ('arg','two'), ('arg','three')]

    and not

      f.query.allitems() == [('arg', ['one', 'two', 'three'])]

    The latter doesn't make sense because query parameter values cannot
    be composed of sub-values. So finally

      str(f.query) == 'arg=one&arg=two&arg=three'


    Additionally, while the set of allowed characters in URL queries is
    defined in RFC 3986 section 3.4, the format for encoding key=value
    pairs within the query is not. In turn, the parsing of encoded
    key=value query pairs differs between implementations.

    As a compromise to support equal signs in both key=value pair
    encoded queries, like

      https://www.google.com?a=1&b=2

    and non-key=value pair encoded queries, like

      https://www.google.com?===3===

    equal signs are percent encoded in key=value pairs where the key is
    non-empty, e.g.

      https://www.google.com?equal-sign=%3D

    but not encoded in key=value pairs where the key is empty, e.g.

      https://www.google.com?===equal=sign===

    This presents a reasonable compromise to accurately reproduce
    non-key=value queries with equal signs while also still percent
    encoding equal signs in key=value pair encoded queries, as
    expected. See

      https://github.com/gruns/furl/issues/99

    for more details.

    Attributes:
      params: Ordered multivalue dictionary of query parameter key:value
        pairs. Parameters in self.params are maintained URL decoded,
        e.g. 'a b' not 'a+b'.
      strict: Boolean whether or not UserWarnings should be raised if
        improperly encoded query strings are provided to methods that
        take such strings, like load(), add(), set(), remove(), etc.
    """

    # From RFC 3986:
    #   query       = *( pchar / "/" / "?" )
    #   pchar       = unreserved / pct-encoded / sub-delims / ":" / "@"
    #   unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
    #   sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
    #                     / "*" / "+" / "," / ";" / "="
    SAFE_KEY_CHARS = "/?:@-._~!$'()*+,;"
    SAFE_VALUE_CHARS = SAFE_KEY_CHARS + '='

    def __init__(self, query='', strict=False):
        self.strict = strict

        self._params = omdict1D()

        self.load(query)

    def load(self, query):
        pass

    def add(self, args):
        pass

    def set(self, mapping):
        """
        Adopt all mappings in <mapping>, replacing any existing mappings
        with the same key. If a key has multiple values in <mapping>,
        they are all adopted.

        Examples:
          Query({1:1}).set([(1,None),(2,2)]).params.allitems()
            == [(1,None),(2,2)]
          Query({1:None,2:None}).set([(1,1),(2,2),(1,11)]).params.allitems()
            == [(1,1),(2,2),(1,11)]
          Query({1:None}).set([(1,[1,11,111])]).params.allitems()
            == [(1,1),(1,11),(1,111)]

        Returns: <self>.
        """
        pass

    def remove(self, query):
        pass

    @property
    def params(self):
        pass

    @params.setter
    def params(self, params):
        pass

    def encode(self, delimiter='&', quote_plus=True, dont_quote='',
               delimeter=_absent):
        """
        Examples:

          Query('a=a&b=#').encode() == 'a=a&b=%23'
          Query('a=a&b=#').encode(';') == 'a=a;b=%23'
          Query('a+b=c@d').encode(dont_quote='@') == 'a+b=c@d'
          Query('a+b=c@d').encode(quote_plus=False) == 'a%20b=c%40d'

        Until furl v0.4.6, the 'delimiter' argument was incorrectly
        spelled 'delimeter'. For backwards compatibility, accept both
        the correct 'delimiter' and the old, misspelled 'delimeter'.

        Keys and values are encoded application/x-www-form-urlencoded if
        <quote_plus> is True, percent-encoded otherwise.

        <dont_quote> exempts valid query characters from being
        percent-encoded, either in their entirety with dont_quote=True,
        or selectively with dont_quote=<string>, like
        dont_quote='/?@_'. Invalid query characters -- those not in
        self.SAFE_KEY_CHARS, like '#' and '^' -- are always encoded,
        even if included in <dont_quote>. For example:

          Query('#=^').encode(dont_quote='#^') == '%23=%5E'.

        Returns: A URL encoded query string using <delimiter> as the
        delimiter separating key:value pairs. The most common and
        default delimiter is '&', but ';' can also be specified. ';' is
        W3C recommended.
        """
        pass

    def asdict(self):
        pass

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not self == other

    def __bool__(self):
        return len(self.params) > 0
    __nonzero__ = __bool__

    def __str__(self):
        return self.encode()

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, str(self))

    def _items(self, items):
        """
        Extract and return the key:value items from various
        containers. Some containers that could hold key:value items are

          - List of (key,value) tuples.
          - Dictionaries of key:value items.
          - Multivalue dictionary of key:value items, with potentially
            repeated keys.
          - Query string with encoded params and values.

        Keys and values are passed through unmodified unless they were
        passed in within an encoded query string, like
        'a=a%20a&b=b'. Keys and values passed in within an encoded query
        string are unquoted by urlparse.parse_qsl(), which uses
        urllib.unquote_plus() internally.

        Returns: List of items as (key, value) tuples. Keys and values
        are passed through unmodified unless they were passed in as part
        of an encoded query string, in which case the final keys and
        values that are returned will be unquoted.

        Raises: UserWarning if <path> is an improperly encoded path
        string and self.strict is True.
        """
        pass

    def _extract_items_from_querystr(self, querystr):
        pass


@six.add_metaclass(abc.ABCMeta)
class QueryCompositionInterface(object):

    """
    Abstract class interface for a parent class that contains a Query.
    """

    def __init__(self, strict=False):
        self._query = Query(strict=strict)

    @property
    def query(self):
        pass

    @property
    def querystr(self):
        """This method is deprecated. Use str(furl.query) instead."""
        pass

    @property
    def args(self):
        """
        Shortcut method to access the query parameters, self._query.params.
        """
        pass

    def __setattr__(self, attr, value):
        """
        Returns: True if this attribute is handled and set here, False
        otherwise.
        """
        if attr == 'args' or attr == 'query':
            self._query.load(value)
            return True
        return False


class Fragment(FragmentPathCompositionInterface, QueryCompositionInterface):

    """
    Represents a URL fragment, comprised internally of a Path and Query
    optionally separated by a '?' character.

      http://tools.ietf.org/html/rfc3986#section-3.5

    Attributes:
      path: Path object from FragmentPathCompositionInterface.
      query: Query object from QueryCompositionInterface.
      separator: Boolean whether or not a '?' separator should be
        included in the string representation of this fragment. When
        False, a '?' character will not separate the fragment path from
        the fragment query in the fragment string. This is useful to
        build fragments like '#!arg1=val1&arg2=val2', where no
        separating '?' is desired.
    """

    def __init__(self, fragment='', strict=False):
        FragmentPathCompositionInterface.__init__(self, strict=strict)
        QueryCompositionInterface.__init__(self, strict=strict)
        self.strict = strict
        self.separator = True

        self.load(fragment)

    def load(self, fragment):
        pass

    def add(self, path=_absent, args=_absent):
        pass

    def set(self, path=_absent, args=_absent, separator=_absent):
        pass

    def remove(self, fragment=_absent, path=_absent, args=_absent):
        pass

    def asdict(self):
        pass

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not self == other

    def __setattr__(self, attr, value):
        if (not PathCompositionInterface.__setattr__(self, attr, value) and
                not QueryCompositionInterface.__setattr__(self, attr, value)):
            object.__setattr__(self, attr, value)

    def __bool__(self):
        return bool(self.path) or bool(self.query)
    __nonzero__ = __bool__

    def __str__(self):
        path, query = str(self._path), str(self._query)

        # If there is no query or self.separator is False, decode all
        # '?' characters in the path from their percent encoded form
        # '%3F' to '?'. This allows for fragment strings containg '?'s,
        # like '#dog?machine?yes'.
        if path and (not query or not self.separator):
            path = path.replace('%3F', '?')

        separator = '?' if path and query and self.separator else ''

        return path + separator + query

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, str(self))


@six.add_metaclass(abc.ABCMeta)
class FragmentCompositionInterface(object):

    """
    Abstract class interface for a parent class that contains a
    Fragment.
    """

    def __init__(self, strict=False):
        self._fragment = Fragment(strict=strict)

    @property
    def fragment(self):
        pass

    @property
    def fragmentstr(self):
        """This method is deprecated. Use str(furl.fragment) instead."""
        pass

    def __setattr__(self, attr, value):
        """
        Returns: True if this attribute is handled and set here, False
        otherwise.
        """
        if attr == 'fragment':
            self.fragment.load(value)
            return True
        return False


class furl(URLPathCompositionInterface, QueryCompositionInterface,
           FragmentCompositionInterface, UnicodeMixin):

    """
    Object for simple parsing and manipulation of a URL and its
    components.

      scheme://username:password@host:port/path?query#fragment

    Attributes:
      strict: Boolean whether or not UserWarnings should be raised if
        improperly encoded path, query, or fragment strings are provided
        to methods that take such strings, like load(), add(), set(),
        remove(), etc.
      username: Username string for authentication. Initially None.
      password: Password string for authentication with
        <username>. Initially None.
      scheme: URL scheme. A string ('http', 'https', '', etc) or None.
        All lowercase. Initially None.
      host: URL host (hostname, IPv4 address, or IPv6 address), not
        including port. All lowercase. Initially None.
      port: Port. Valid port values are 1-65535, or None meaning no port
        specified.
      netloc: Network location. Combined host and port string. Initially
      None.
      path: Path object from URLPathCompositionInterface.
      query: Query object from QueryCompositionInterface.
      fragment: Fragment object from FragmentCompositionInterface.
    """

    def __init__(self, url='', args=_absent, path=_absent, fragment=_absent,
                 scheme=_absent, netloc=_absent, origin=_absent,
                 fragment_path=_absent, fragment_args=_absent,
                 fragment_separator=_absent, host=_absent, port=_absent,
                 query=_absent, query_params=_absent, username=_absent,
                 password=_absent, strict=False):
        """
        Raises: ValueError on invalid URL or invalid URL component(s) provided.
        """
        URLPathCompositionInterface.__init__(self, strict=strict)
        QueryCompositionInterface.__init__(self, strict=strict)
        FragmentCompositionInterface.__init__(self, strict=strict)
        self.strict = strict

        self.load(url)  # Raises ValueError on invalid URL.
        self.set(  # Raises ValueError on invalid URL component(s).
            args=args, path=path, fragment=fragment, scheme=scheme,
            netloc=netloc, origin=origin, fragment_path=fragment_path,
            fragment_args=fragment_args, fragment_separator=fragment_separator,
            host=host, port=port, query=query, query_params=query_params,
            username=username, password=password)

    def load(self, url):
        """
        Parse and load a URL.

        Raises: ValueError on invalid URL, like a malformed IPv6 address
        or invalid port.
        """
        pass

    @property
    def scheme(self):
        pass

    @scheme.setter
    def scheme(self, scheme):
        pass

    @property
    def host(self):
        pass

    @host.setter
    def host(self, host):
        """
        Raises: ValueError on invalid host or malformed IPv6 address.
        """
        pass

    @property
    def port(self):
        pass

    @port.setter
    def port(self, port):
        """
        The port value can be 1-65535 or None, meaning no port specified. If
        <port> is None and self.scheme is a known scheme in DEFAULT_PORTS,
        the default port value from DEFAULT_PORTS will be used.

        Raises: ValueError on invalid port.
        """
        pass

    @property
    def netloc(self):
        pass

    @netloc.setter
    def netloc(self, netloc):
        """
        Params:
          netloc: Network location string, like 'google.com' or
            'user:pass@google.com:99'.
        Raises: ValueError on invalid port or malformed IPv6 address.
        """
        pass

    @property
    def origin(self):
        pass

    @origin.setter
    def origin(self, origin):
        pass

    @property
    def url(self):
        pass

    @url.setter
    def url(self, url):
        pass

    def add(self, args=_absent, path=_absent, fragment_path=_absent,
            fragment_args=_absent, query_params=_absent):
        """
        Add components to a URL and return this furl instance, <self>.

        If both <args> and <query_params> are provided, a UserWarning is
        raised because <args> is provided as a shortcut for
        <query_params>, not to be used simultaneously with
        <query_params>. Nonetheless, providing both <args> and
        <query_params> behaves as expected, with query keys and values
        from both <args> and <query_params> added to the query - <args>
        first, then <query_params>.

        Parameters:
          args: Shortcut for <query_params>.
          path: A list of path segments to add to the existing path
            segments, or a path string to join with the existing path
            string.
          query_params: A dictionary of query keys and values or list of
            key:value items to add to the query.
          fragment_path: A list of path segments to add to the existing
            fragment path segments, or a path string to join with the
            existing fragment path string.
          fragment_args: A dictionary of query keys and values or list
            of key:value items to add to the fragment's query.

        Returns: <self>.

        Raises: UserWarning if redundant and possibly conflicting <args> and
        <query_params> were provided.
        """
        pass

    def set(self, args=_absent, path=_absent, fragment=_absent, query=_absent,
            scheme=_absent, username=_absent, password=_absent, host=_absent,
            port=_absent, netloc=_absent, origin=_absent, query_params=_absent,
            fragment_path=_absent, fragment_args=_absent,
            fragment_separator=_absent):
        """
        Set components of a url and return this furl instance, <self>.

        If any overlapping, and hence possibly conflicting, parameters
        are provided, appropriate UserWarning's will be raised. The
        groups of parameters that could potentially overlap are

          <scheme> and <origin>
          <origin>, <netloc>, and/or (<host> or <port>)
          <fragment> and (<fragment_path> and/or <fragment_args>)
          any two or all of <query>, <args>, and/or <query_params>

        In all of the above groups, the latter parameter(s) take
        precedence over the earlier parameter(s). So, for example

          furl('http://google.com/').set(
            netloc='yahoo.com:99', host='bing.com', port=40)

        will result in a UserWarning being raised and the url becoming

          'http://bing.com:40/'

        not

          'http://yahoo.com:99/

        Parameters:
          args: Shortcut for <query_params>.
          path: A list of path segments or a path string to adopt.
          fragment: Fragment string to adopt.
          scheme: Scheme string to adopt.
          netloc: Network location string to adopt.
          origin: Scheme and netloc.
          query: Query string to adopt.
          query_params: A dictionary of query keys and values or list of
            key:value items to adopt.
          fragment_path: A list of path segments to adopt for the
            fragment's path or a path string to adopt as the fragment's
            path.
          fragment_args: A dictionary of query keys and values or list
            of key:value items for the fragment's query to adopt.
          fragment_separator: Boolean whether or not there should be a
            '?' separator between the fragment path and fragment query.
          host: Host string to adopt.
          port: Port number to adopt.
          username: Username string to adopt.
          password: Password string to adopt.
        Raises:
          ValueError on invalid port.
          UserWarning if <scheme> and <origin> are provided.
          UserWarning if <origin>, <netloc> and/or (<host> and/or <port>) are
            provided.
          UserWarning if <query>, <args>, and/or <query_params> are provided.
          UserWarning if <fragment> and (<fragment_path>,
            <fragment_args>, and/or <fragment_separator>) are provided.
        Returns: <self>.
        """
        pass

    def remove(self, args=_absent, path=_absent, fragment=_absent,
               query=_absent, scheme=False, username=False, password=False,
               host=False, port=False, netloc=False, origin=False,
               query_params=_absent, fragment_path=_absent,
               fragment_args=_absent):
        """
        Remove components of this furl's URL and return this furl
        instance, <self>.

        Parameters:
          args: Shortcut for query_params.
          path: A list of path segments to remove from the end of the
            existing path segments list, or a path string to remove from
            the end of the existing path string, or True to remove the
            path portion of the URL entirely.
          query: A list of query keys to remove from the query, if they
            exist, or True to remove the query portion of the URL
            entirely.
          query_params: A list of query keys to remove from the query,
            if they exist.
          port: If True, remove the port from the network location
            string, if it exists.
          fragment: If True, remove the fragment portion of the URL
            entirely.
          fragment_path: A list of path segments to remove from the end
            of the fragment's path segments or a path string to remove
            from the end of the fragment's path string.
          fragment_args: A list of query keys to remove from the
            fragment's query, if they exist.
          username: If True, remove the username, if it exists.
          password: If True, remove the password, if it exists.
        Returns: <self>.
        """
        pass

    def tostr(self, query_delimiter='&', query_quote_plus=True,
              query_dont_quote=''):
        pass

    def join(self, *urls):
        pass

    def copy(self):
        pass

    def asdict(self):
        pass

    def __truediv__(self, path):
        return self.copy().add(path=path)

    def __eq__(self, other):
        try:
            return self.url == other.url
        except AttributeError:
            return None

    def __ne__(self, other):
        return not self == other

    def __setattr__(self, attr, value):
        if (not PathCompositionInterface.__setattr__(self, attr, value) and
           not QueryCompositionInterface.__setattr__(self, attr, value) and
           not FragmentCompositionInterface.__setattr__(self, attr, value)):
            object.__setattr__(self, attr, value)

    def __unicode__(self):
        return self.tostr()

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, str(self))
