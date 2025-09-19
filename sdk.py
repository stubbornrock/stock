import uuid
import json
import hmac
import base64
import requests
import hashlib
import datetime
import configparser
import urllib.parse
from urllib.parse import quote
from enum import Enum

# Configs
#zhangpeng
ak = "d67caad761244673bfdead8a5300125e"
sk = "b8312fef99b74778b31e7eb9c436a78a"
debug = False
#zgcxy
#ak = 'e9f467655cad41b39a06566245941b5e'
#sk = '313c0a9c02f64afaaf7a066f48b2bd47'
#sina
#ak = "0212931a4d9e4449bcfbff5ae6eb812b"
#sk = "9d6fb4fe404c4a1385377d23f6d5772b"

class REQ(Enum):
    GET = 'GET'
    POST = 'POST'

def print_log(log_info):
   if debug:
        now = datetime.datetime.now()
        log_info = '[%s]: %s' % (str(now), log_info)
        print(log_info)
   else:
        pass

# HMAC 
def _hmac_sha256(secret, message):
    '''
    HMAC is a hash-based message authentication code that combines a secret key with the message content, generating a fixed-length output value through a hash algorithm. 
    It can be used for message integrity verification and data authentication.
    '''
    if type(secret) == bytes:
        secret = bytearray(secret)
    else:
        secret = bytearray(secret, 'utf8')
    data = bytearray(message, 'utf8')
    return hmac.new(secret, data, digestmod=hashlib.sha256).digest()

# Base64 Encode
def _base64_of_hmac(data):
    return base64.b64encode(data)

# URL encode & sorted
def _urlSortandEncode(data):
    sorted_data = sorted(data.items(), key=lambda item: item[0])
    #str_list = map(lambda xy: '%s=%s' % (xy[0], quote(str(xy[1]))), sorted_data)
    #str_list = map(lambda xy: '%s=%s' % (xy[0], quote(xy[1])), sorted_data)
    str_list = []
    for xy in sorted_data:
        x = xy[0]
        y = xy[1]
        if type(y) == str:
            y = quote(y)
        str_list.append('%s=%s' %(x,y))
    return '&'.join(str_list)


def _eop_auth(query_params, body_params, eop_date, request_uuid, method):
    # body_params digest
    body_str = json.dumps(body_params) if body_params else ''
    if method == REQ.GET:
        body_digest = hashlib.sha256(body_str.encode('utf-8')).hexdigest()
    else:
        if isinstance(body_params, dict):
            body_digest = hashlib.sha256(json.dumps(body_params).encode('utf-8')).hexdigest()
        else:
            body_digest = hashlib.sha256(body_params.encode('utf-8')).hexdigest()
    # headers_str
    header_str = 'ctyun-eop-request-id:%s\neop-date:%s\n' % (request_uuid, eop_date)
    # query_str
    query_str = _urlSortandEncode(query_params)

    signature_str = '%s\n%s\n%s' % (header_str, query_str, body_digest)
    print_log(repr('signature_str is: %s' % signature_str))

    # Constructing Dynamic Keys
    # When making a request, you need to construct an eop-date timestamp, which follows the format yyyymmddTHHMMSSZ
    # First, use the ctyun-eop-sk (your secret key) as the key and eop-date as the data to compute ktime. 
    # Next, use ktime as the key and ctyun-eop-ak (your access key) as the data to compute kAk. 
    # Finally, use kAk as the key and the year, month, and day part of eop-date as the data to compute kdate.
    sign_date = eop_date.split('T')[0]
    k_time = _hmac_sha256(sk, eop_date)
    k_ak = _hmac_sha256(k_time, ak)
    k_date = _hmac_sha256(k_ak, sign_date)

    signature_base64 = _base64_of_hmac(_hmac_sha256(k_date, signature_str))

    # 
    sign_header = '%s Headers=ctyun-eop-request-id;eop-date Signature=%s' % (ak, signature_base64.decode('utf8'))
    print_log("sign_header is: " + sign_header)
    return sign_header.encode('utf8')

def _sign_headers(query_params, body_params, method, content_type):
    # Generate eop_date
    now = datetime.datetime.now()
    eop_date = datetime.datetime.strftime(now, '%Y%m%dT%H%M%SZ')
    # Generate request_uuid
    request_uuid = str(uuid.uuid1())

    # Generate Headers
    headers = {
        'ctyun-eop-request-id': request_uuid,
        'Eop-Authorization': _eop_auth(query_params=query_params,body_params=body_params,eop_date=eop_date,request_uuid=request_uuid,method=method),
        'Eop-date': eop_date,
    }
    return headers


# Execute Http request
def execute(url, method=None, query_params={}, header_params={}, body_params={}):

    # GET request!
    if method == REQ.GET:
        # Merge query&body params
        params = {**query_params, **body_params}
        query_params, body_params = (params, {})
    headers = _sign_headers(query_params, body_params, method, header_params['Content-Type'])
    headers.update(header_params)
    headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/110.0"})

    # URLEncode
    #if 'application/x-www-form-urlencoded' in header_params['Content-Type']:
    #    #regionID=bb9fdb42056f11eda1610242ac110002&azName=cn-huadong1-jsnj2A-public-ctcloud
    #   params = urllib.parse.urlencode(params)

    #url = url + "?" + _urlSortandEncode(query_params)
    print_log('url: %s' % url)
    print_log('Request-Method: %s' % method)
    print_log('Request-Headers: %s' % headers)
    print_log('Request-Params: %s' % body_params)
    print_log('Request-Type: %s' % type(body_params))
    requests.packages.urllib3.disable_warnings()
    if method == REQ.GET:
        res = requests.get(url, params=params, headers=headers, verify=False)
    else:
        if 'application/x-www-form-urlencoded' in header_params['Content-Type']:
            res = requests.post(url, data=body_params, headers=headers, verify=False)
        elif 'multipart/form-data' in header_params['Content-Type']:
            res = requests.post(url, data=body_params, headers=headers, verify=False)
        else:
            res = requests.post(url, json=body_params, headers=headers, verify=False)

    print_log('Response-StatusCode: %s' % res.status_code)
    #print_log('Respone: %s' % res.json())
    return res
    
# get
def get(url, query_params={}, header_params={}, body_params={}):
    return execute(url, method=REQ.GET, query_params=query_params, header_params=header_params, body_params=body_params)

# post
def post(url, query_params={}, header_params={}, body_params={}):
    return execute(url, method=REQ.POST, query_params=query_params, header_params=header_params, body_params=body_params)
