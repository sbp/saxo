# http://inamidst.com/saxo/
# Created by Sean B. Palmer

import html.entities
import re
import urllib.parse
import urllib.request

# NOTE: (?i) does work in byte instances
_regex_charset = re.compile(b"(?i)<meta[^>]+charset=[\"']?([^\"'> \r\n\t]+)")
_regex_entity = re.compile(r"&([^;\s]+);")
_regex_key = re.compile(r'([^=]+)')
_regex_value = re.compile(r'("[^"\\]*(?:\\.[^"\\]*)*"|[^;]+)')

user_agent = "Mozilla/5.0 (Services)"
# modern_user_agent = " ".join([
#     "Mozilla/5.0",
#     "(Macintosh; Intel Mac OS X 10.9; rv:26.0)"
#     "Gecko/20100101 Firefox/26.0"])
modern_user_agent = " ".join([
    "Mozilla/5.0",
    "(Macintosh; Intel Mac OS X 10.10; rv:37.0)"
    "Gecko/20100101 Firefox/37.0"])

def content_type(info):
    mime = None
    encoding = None

    def parse(parameters):
        while parameters:
            match = _regex_key.match(parameters)
            if not match:
                break

            key = match.group(1)
            parameters = parameters[len(key):]
            if parameters.startswith("="):
                parameters = parameters[1:]

            match = _regex_value.match(parameters)
            if not match:
                break

            value = match.group(1)
            if value.startswith('"'):
                value = value[1:-1].replace('\\"', '"')
            parameters = parameters[len(value):]

            if parameters.startswith(";"):
                parameters = parameters[1:]

            key = key.lower().strip(" \t")
            value = value.lower().strip(" \t")
            yield key, value

    if "Content-Type" in info:
        header = info["Content-Type"]
        if ";" in header:
            mime, parameters = header.split(";", 1)
        else:
            mime, parameters = header, ""

        for key, value in parse(parameters):
            if key == "charset":
                encoding = value
                break
    return mime, encoding

def decode_entities(hypertext):
    def entity(match):
        name = match.group(1).lower()

        if name.startswith("#x"):
            return chr(int(name[2:], 16))
        elif name.startswith("#"):
            return chr(int(name[1:]))
        elif name in html.entities.name2codepoint:
            return chr(html.entities.name2codepoint[name])
        return "[" + name + "]"

    def default(match):
        try: return entity(match)
        except: return match.group(1)
    return _regex_entity.sub(default, hypertext)

def construct(url, query=None):
    safe = "".join(chr(i) for i in range(0x01, 0x80))
    base = urllib.parse.quote(url, safe=safe)
    if query:
        query = urllib.parse.urlencode(query)
        return "?".join((base, query))
    return base

def request(url, query=None, data=None, method="GET",
        limit=None, follow=True, headers=None, modern=False):
    if url.startswith("file:"):
        raise ValueError("file: scheme is not allowed")
    headers = {} if (headers is None) else headers

    response = {}
    if "User-Agent" not in headers:
        modern = modern is True
        headers["User-Agent"] = modern_user_agent if modern else user_agent
    response["request-headers"] = headers

    parts = list(urllib.parse.urlparse(url))
    try: parts[1].encode("ascii")
    except UnicodeEncodeError:
        parts[1] = parts[1].encode("idna").decode("ascii")
        url = urllib.parse.urlunparse(tuple(parts))

    safe = "".join(chr(i) for i in range(0x01, 0x80))
    base = urllib.parse.quote(url, safe=safe)
    if query:
        query = urllib.parse.urlencode(query)
        response["request-url"] = "?".join((base, query))
    else:
        response["request-url"] = base

    class ErrorHandler(urllib.request.HTTPDefaultErrorHandler):
        def http_error_default(self, req, fp, code, msg, hdrs):
            return fp

    handlers = [ErrorHandler()]
    if follow:
        handlers.append(urllib.request.HTTPRedirectHandler())

    opener = urllib.request.build_opener(*handlers)
    urllib.request.install_opener(opener)

    params = {
        "url": response["request-url"],
        "headers": response["request-headers"]
    }

    if data is not None:
        if isinstance(data, dict):
            data = urllib.parse.urlencode(data)
            params["data"] = data.encode("utf-8", "replace")
        elif isinstance(data, bytes):
            params["data"] = data
        elif isinstance(data, str):
            params["data"] = data.encode("utf-8", "replace")
        else:
            raise Exception("Unknown data type: %s" % type(data))

    # print("PARAMS:", params)
    req = urllib.request.Request(**params)
    with urllib.request.urlopen(req) as res:
        response["url"] = res.url
        response["status"] = res.status # int
        response["info"] = res.info()
        response["headers"] = {
            a.lower(): b for (a, b) in response["info"].items()
        }

        if method in {"GET", "POST"}:
            if limit is None:
                response["octets"] = res.read()
            else:
                response["octets"] = res.read(limit)

    if "Content-Encoding" in response["info"]:
        if response["info"]["Content-Encoding"] == "gzip":
            from gzip import GzipFile
            from io import BytesIO
            sio = BytesIO(response["octets"])
            gz = GzipFile(fileobj=sio)
            try: response["octets"] = gz.read()
            except OSError:
                # e.g. not gzip encoded, despite the site saying it is
                ...

    mime, encoding = content_type(response["info"])
    if mime:
        response["mime"] = mime
    if encoding:
        response["encoding"] = encoding
        response["encoding-source"] = "Content-Type"

    if mime and ("octets" in response):
        if ("/html" in mime) or ("/xhtml" in mime):
            search = _regex_charset.search(response["octets"])
            if search:
                html_encoding = search.group(1).lower()
                html_encoding = html_encoding.decode("ascii", "replace")

                if encoding and (encoding == html_encoding):
                        response["encoding-source"] += ", HTML"
                else: # TODO: Precedence check
                    response["encoding"] = html_encoding
                    response["encoding-source"] = "HTML"

    if "octets" in response:
        def guess_encoding(response):
            try: response["text"] = response["octets"].decode("utf-8")
            except UnicodeDecodeError:
                response["text"] = response["octets"].decode("iso-8859-1")
                response["encoding"] = "iso-8859-1"
            else:
                response["encoding"] = "utf-8"
            response["encoding-source"] = "heuristic"

        if "encoding" in response:
            encoding = response["encoding"]
            try: response["text"] = response["octets"].decode(encoding)
            except (UnicodeDecodeError, LookupError):
                guess_encoding(response)
        else:
            guess_encoding(response)

    if mime and ("text" in response):
        if ("/html" in mime) or ("/xhtml" in mime):
                response["html"] = response["text"]
                response["text"] = decode_entities(response["text"])
                response["decoded-entities"] = True

    return response
