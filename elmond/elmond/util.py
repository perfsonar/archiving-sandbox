import logging
import datetime
import isodate
import time
from socket import getaddrinfo, AF_INET, AF_INET6, SOL_TCP, SOCK_STREAM
from summaries import INVERSE_SUMMARY_TYPES
from werkzeug.exceptions import BadRequest

log = logging.getLogger('elmond')

#Constants
BASE_URI="/esmond/perfsonar/archive"
TIME_FILTER = "time"
TIME_START_FILTER = "time-start"
TIME_END_FILTER = "time-end"
TIME_RANGE_FILTER = "time-range"
LIMIT_FILTER = "limit"
OFFSET_FILTER = "offset"

def iso8601_to_seconds(val):
    """Convert an ISO 8601 string to a timdelta"""
    # TODO: Decide what to do with months or years.
    try:
        td = isodate.parse_duration(val)
    except isodate.isoerror.ISO8601Error:
        return None
    if type(td) != datetime.timedelta:
        return None
    
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10.0**6) / 10.0**6

def build_uri(md_key, event_type=None, summary_type='base', summary_window=0):
    if event_type:
        if summary_type in INVERSE_SUMMARY_TYPES:
            summary_type = INVERSE_SUMMARY_TYPES[summary_type]
        uri = "{0}/{1}/{2}/{3}/{4}".format(BASE_URI, md_key, event_type, summary_type, summary_window)
    else:
        uri = "{0}/{1}".format(BASE_URI, md_key)
    
    return uri

def lookup_hostname(host, family):
    """
    Does a lookup of the IP for host in type family (i.e. AF_INET or AF_INET6)
    """
    addr = None
    addr_info = None
    try:
        addr_info = getaddrinfo(host, 80, family, SOCK_STREAM, SOL_TCP)
    except:
        pass
    if addr_info and len(addr_info) >= 1 and len(addr_info[0]) >= 5 and len(addr_info[0][4]) >= 1:
        addr = addr_info[0][4][0]
    
    return addr

def valid_time(t):
    try:
        t = int(t)
    except ValueError:
        raise BadRequest("Time parameter must be an integer")
    return t
    
def handle_time_filters(filters):
        end_time = int(time.time())
        begin_time = 0
        has_filters = True
        if TIME_FILTER in filters:
            begin_time = valid_time(filters[TIME_FILTER])
            end_time = begin_time
        elif TIME_START_FILTER in filters and TIME_END_FILTER in filters:
            begin_time = valid_time(filters[TIME_START_FILTER])
            end_time = valid_time(filters[TIME_END_FILTER])
        elif TIME_START_FILTER in filters and TIME_RANGE_FILTER in filters:
            begin_time = valid_time(filters[TIME_START_FILTER])
            end_time = begin_time + valid_time(filters[TIME_RANGE_FILTER])
        elif TIME_END_FILTER in filters and TIME_RANGE_FILTER in filters:
            end_time = valid_time(filters[TIME_END_FILTER])
            begin_time = end_time - valid_time(filters[TIME_RANGE_FILTER])
        elif TIME_START_FILTER in filters:
            begin_time = valid_time(filters[TIME_START_FILTER])
            end_time = None
        elif TIME_END_FILTER in filters:
            end_time = valid_time(filters[TIME_END_FILTER])
        elif TIME_RANGE_FILTER in filters:
            begin_time = end_time - valid_time(filters[TIME_RANGE_FILTER])
            end_time = None
        else:
            has_filters = False
        if (end_time is not None) and (end_time < begin_time):
            raise BadRequest("Requested start time must be less than end time")
        return {"begin": begin_time,
                "end": end_time,
                "has_filters": has_filters}
    
