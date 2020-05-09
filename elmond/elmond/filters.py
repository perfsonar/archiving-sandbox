import logging
import re
from socket import AF_INET, AF_INET6
from summaries import DEFAULT_SUMMARIES
from util import *
from werkzeug.exceptions import BadRequest

log = logging.getLogger('elmond')

MAPPED_FILTERS = {
    #standard
    "input-source": "test.spec.source",
    "input-destination": "test.spec.dest",
    "metadata-key": "pscheduler.test_checksum",
    "pscheduler-test-type": "test.type",
    #type-specific
    "bw-buffer-size": "test.spec.buffer-length",
    "bw-parallel-streams": "test.spec.parallel",
    "bw-target-bandwidth": "test.spec.bandwidth",
    "bw-ignore-first-seconds": "test.spec.omit",
    "ip-dscp": "test.spec.dscp",
    "ip-fragment": "test.spec.fragment",
    "ip-packet-flowlabel": "test.spec.flowlabel",
    "ip-packet-padding": "test.spec.packet-padding",
    "ip-packet-size": "test.spec.length",
    "ip-tos": "test.spec.tos",
    "ip-ttl": "test.spec.ttl",
    "mode-flip": "test.spec.flip", 
    "mode-single-participant": "test.spec.single-participant-mode",
    "sample-bucket-width": "test.spec.bucket-width", 
    "tcp-window-size": "test.spec.window-size",
    "tcp-dynamic-window-size": "test.spec.dynamic-window-size",
    "tcp-max-segment-size": "test.spec.mss",    
    "trace-algorithm": "test.spec.algorithm",
    "trace-first-ttl": "test.spec.first-ttl",
    "trace-max-ttl": "test.spec.hops",
    "trace-num-queries": "test.spec.queries"
}

MULTI_FILTERS = {
    "sample-size": ["test.spec.packet-count", "test.spec.count"],
    "time-probe-interval": ["test.spec.packet-interval", "test.spec.interval", "test.spec.sendwait"],
    "time-probe-timeout": ["test.spec.packet-timeout", "test.spec.deadline"],
    "time-test-timeout": ["test.spec.timeout", "test.spec.wait"]
}

IP_FILTERS = {
    "source": "meta.source.ip",
    "destination": "meta.destination.ip",
    "measurement-agent": "meta.observer.ip"
}

P2P_TESTS = [
    "disk-to-disk",
    "latency",
    "latencybg",
    "rtt",
    "throughput",
    "trace"
]

TRANSLATE_EVENT_TYPE = {
    "histogram-owdelay": ["latency","latencybg"],
    "histogram-ttl": ["latency","latencybg"],
    "histogram-ttl-reverse": ["rtt"],
    "histogram-rtt": ["rtt"],
    "packet-count-lost": ["latency","latencybg", "throughput"],
    "packet-count-lost-bidir": ["rtt"],
    "packet-count-sent": ["latency","latencybg", "throughput", "rtt"],
    "packet-duplicates": ["latency","latencybg"],
    "packet-duplicates-bidir": ["rtt"],
    "packet-loss-rate": ["latency","latencybg", "throughput"],
    "packet-loss-rate-bidir": ["rtt"],
    "packet-reorders": ["latency","latencybg"],
    "packet-reorders-bidir": ["rtt"],
    "packet-retransmits": ["throughput"],
    "packet-retransmits-subintervals": ["throughput"],
    "packet-trace": ["trace"],
    "packet-trace-multi": ["trace"],
    "path-mtu": ["trace"],
    "streams-packet-retransmits": ["throughput"],
    "streams-packet-retransmits-subintervals": ["throughput"],
    "streams-throughput": ["throughput"],
    "streams-throughput-subintervals": ["throughput"],
    "throughput": ["throughput", "disk-to-disk"],
    "throughput-subintervals": ["throughput"],
    "time-error-estimates": ["latency","latencybg"],
}

'''
Constants that map to common filters
'''
DNS_MATCH_RULE_FILTER = "dns-match-rule"
DNS_MATCH_PREFER_V6 = "prefer-v6"
DNS_MATCH_PREFER_V4 = "prefer-v4"
DNS_MATCH_ONLY_V6 = "only-v6"
DNS_MATCH_ONLY_V4 = "only-v4"
DNS_MATCH_V4_V6 = "v4v6"
RESERVED_GET_PARAMS = [
    "format", 
    LIMIT_FILTER, 
    OFFSET_FILTER, 
    DNS_MATCH_RULE_FILTER, 
    TIME_FILTER,
    TIME_START_FILTER, 
    TIME_END_FILTER, 
    TIME_RANGE_FILTER, 
    "event-type",
    "summary-type",
    "summary-window"
]

def _build_term(key, value):
    return {
        "term": {
            key: value
        }
    }

def _build_gte(key, value):
    return {
        "range": {
            key: {
                "gte": value
            }
        }
    }
    
def _build_key_or(keys, value):
    filter = {
        "bool": {
          "should": []
        }
    }
    for key in keys:
        filter["bool"]["should"].append(_build_term(key, value))
    
    return filter

def _build_val_or(key, values):
    filter = {
        "bool": {
          "should": []
        }
    }
    for value in values:
        filter["bool"]["should"].append(_build_term(key, value))
    
    return filter

def _build_ip_filter(key, host, dns_match_rule=DNS_MATCH_V4_V6):
    #get IP address
    addrs = []
    addr4 = None
    addr6 = None
    if dns_match_rule == DNS_MATCH_ONLY_V6:
        addr6 = lookup_hostname(host, AF_INET6)
    elif dns_match_rule == DNS_MATCH_ONLY_V4:
        addr4 = lookup_hostname(host, AF_INET)
    elif dns_match_rule == DNS_MATCH_PREFER_V6:
        addr6 = lookup_hostname(host, AF_INET6)
        if addr6 is None:
            addr4 = lookup_hostname(host, AF_INET)
    elif dns_match_rule == DNS_MATCH_PREFER_V4:
        addr4 = lookup_hostname(host, AF_INET)
        if addr4 is None:
            addr6 = lookup_hostname(host, AF_INET6)
    elif dns_match_rule == DNS_MATCH_V4_V6:
        addr6 = lookup_hostname(host, AF_INET6)
        addr4 = lookup_hostname(host, AF_INET)
    else:
        raise BadRequest("Invalid dns-match-rule parameter {0}".format(dns_match_rule))
        
    #add results to list
    if addr4: addrs.append(addr4)
    if addr6: addrs.append(addr6)
    if len(addrs) == 0:
        raise BadRequest("Unable to find address for host {0}".format(host))
    
    #build filter
    return _build_val_or(key, addrs)

def _build_event_type(event_type, summary_type, summary_window): 
    event_types = []
    if summary_type or summary_window:
        #if we have summary_type and/or window, make sure we have a useable combo
        matching_et_map = {}
        for et in DEFAULT_SUMMARIES:
            if event_type is None or event_type == et:
                for s in DEFAULT_SUMMARIES[et]:
                    if summary_type is None or summary_type == s['summary-type']:
                        if summary_window is None or int(summary_window) == s['summary-window']:
                            matching_et_map[et] = True
        if matching_et_map:
            event_types = matching_et_map.keys() 
        else:
            #impossible to match anything
            return None
    elif event_type:
        #if just event type, that's easy
        event_types.append(event_type) 
    
    #built a map of test types we need
    test_type_map = {}
    for e in event_types:
        if e in TRANSLATE_EVENT_TYPE:
            for te in TRANSLATE_EVENT_TYPE[e]:
                test_type_map[te] = True
        elif e == "pscheduler-run-href" or "pscheduler-raw":
            #could be anything
            return []
        else:
            #bad event type
            raise BadRequest("Invalid event-type parameter {0}".format(e))
    
    #now that we have test types, build the filter
    #this is imperfect because some events only present
    # when other parameters are set 
    # like throughput tests with udp set also report loss but not retransmits
    filter = {
        "bool": {
          "should": []
        }
    }
    for test_type in test_type_map:
        if event_type and test_type == "throughput":
            must_filter = { "bool": { "must": [] } }
            if event_type.startswith("streams-packet-retransmits"):
                #must have parrallel >= 2 and NOT be UDP
                must_filter["bool"]["must"].append(_build_term("test.type", test_type))
                must_filter["bool"]["must"].append(_build_gte("test.spec.parallel", 2))
                must_filter["bool"]["must_not"] = _build_term("test.spec.udp", True)
                filter["bool"]["should"].append(must_filter)
            elif event_type.startswith("streams-"):
                #must have parrallel >= 2
                must_filter["bool"]["must"].append(_build_term("test.type", test_type))
                must_filter["bool"]["must"].append(_build_gte("test.spec.parallel", 2))
                filter["bool"]["should"].append(must_filter)
            elif event_type.startswith("packet-retransmits"):
                #must NOT be UDP
                must_filter["bool"]["must"].append(_build_term("test.type", test_type))
                must_filter["bool"]["must_not"] = _build_term("test.spec.udp", True)
                filter["bool"]["should"].append(must_filter)
            elif event_type.startswith("packet-"):
                #must be UDP
                must_filter["bool"]["must"].append(_build_term("test.type", test_type))
                must_filter["bool"]["must"] = _build_term("test.spec.udp", True)
                filter["bool"]["should"].append(must_filter)
            else:
                #everything else, just check the type
                filter["bool"]["should"].append(_build_term("test.type", test_type))
        elif event_type == "packet-trace-multi":
            #check algorithm is 'paris-traceroute'
            must_filter = { "bool": { "must": [] } }
            must_filter.append(_build_term("test.type", test_type))
            must_filter.append(_build_term("test.spec.algorithm", "paris-traceroute"))
            filter["bool"]["should"].append(must_filter)
        else:
            #everything else just check the test.type
            filter["bool"]["should"].append(_build_term("test.type", test_type))
    
    return filter

def _build_subj_type(value):
    filter = {
        "bool": {
          "should": []
        }
    }
    for t in P2P_TESTS:
        filter["bool"]["should"].append(_build_term("test.type", t))
    if value == "network-element":
        #anything but the point-to-point tests
        filter = {
            "bool": {
                "must_not": filter
                }
        }
    elif value != "point-to-point":
        raise BadRequest("Invalid subject-type {0}.".format(value))
    
    return filter
        
def _build_proto(value):
    filter = {
        "bool": {
          "should": []
        }
    }
    #match for trace. Note that esmond archiver does not set if not specified
    filter["bool"]["should"].append(_build_term("test.spec.probe-type", value.lower()))
    #match for throughput. note esmond archiver always sets to TCP if not UDP
    if value.lower()=='udp':
        # a test with udp set to true
        filter["bool"]["should"].append(_build_term("test.spec.udp", True))
    elif value.lower()=='tcp':
        #any throughput test that doesn't have UDP set to true
        filter["bool"]["must_not"] = _build_term("test.spec.udp", True)
        filter["bool"]["should"].append(_build_term("test.type", "throughput"))
    
    return filter

def build_time_filter(params, time_field="pscheduler.start_time"):
    range_dsl = { "range": { time_field: {} } }
    time_filters = handle_time_filters(params)
    if(time_filters["has_filters"]):
        print("begin_ts={0}, end_ts={1}".format(time_filters['begin'], time_filters['end']))
        begin = datetime.datetime.utcfromtimestamp(time_filters['begin'])
        print("begin={0}".format(begin))
        range_dsl["range"][time_field]["gte"] = begin
        if time_filters['end'] is not None:
            end = datetime.datetime.utcfromtimestamp(time_filters['end'])
            print("end={0}".format(end))
            range_dsl["range"][time_field]["lte"] = end
        return range_dsl
    else:
        return None

def build_filters(params):
    #initialize
    filters = []
    if not params:
        return filters
    
    #handle time filters
    time_filter = build_time_filter(params)
    if time_filter:
        filters.append(time_filter)
    
    # Get dns-match-rule filter
    dns_match_rule = params.get("dns-match-rule", DNS_MATCH_V4_V6)
    
    #handle event and summary filter
    event_type = params.get("event-type", None)
    summary_type = params.get("summary-type", None)
    summary_window = params.get("summary-window", None)
    if event_type or summary_type or summary_window:
        event_filter = _build_event_type(event_type, summary_type, summary_window)
        if event_filter is None:
            #impossible filter
            return None
        else:
            filters.append(event_filter)
    
    #handle filters on fields
    for param in params:
        value = params[param]
        filter = None
        
        if param in RESERVED_GET_PARAMS:
            continue
        elif param in MAPPED_FILTERS:
            #is this a known filter
            key = MAPPED_FILTERS[param]
        elif param in MULTI_FILTERS:
            filter = _build_key_or(MULTI_FILTERS[param], value)
        elif param in IP_FILTERS:
            filter = _build_ip_filter(IP_FILTERS[param], value, dns_match_rule=dns_match_rule)
        elif param == "ip-transport-protocol":
            filter = _build_proto(value)
        elif param == "tool-name":
            key = "pscheduler.tool"
            value = re.sub(r'^pscheduler/', "", value)
        elif param == "subject-type":
            filter = _build_subj_type(value)
        elif param.startswith("pscheduler-reference"):
            #does it start with pscheduler-reference
            #decompose into dotted notation
            key = re.sub(r'^pscheduler-',"", key)
            #The following is prone to error, we have no way to tell if a - 
            # is because its in original key or added by esmond archiver to 
            # separate nested objects. Handle a few known special cases but 
            # otherwise people should avoid hyphens in reference fields
            key = param.replace("-",".")
            #special cases
            key = param.replace("display.set","display-set")
            key = param.replace("psconfig.created.by","psconfig.created-by")
            key = param.replace("psconfig.created-by.user.agent","psconfig.created-by.user-agent")
        elif param.startswith("pscheduler-"):
            #does it start with pscheduler-testtype
            #decompose into dotted notation
            key = re.sub(r'^pscheduler-.+?-', "", key) #remove prefix
            key = re.sub(r'^to-disk-', "", key)#handle special disk-to-disk case
            key = key.replace("-",".")
            key = "test.spec.{0}".format(key)
        else:
            #if doesn't match below, use key as-is and apply to test spec
            # this actually gives you the option to use the mapped or unmapped name
            key = "test.spec.{0}".format(param)
        
        #add the filter to the list
        if filter:
            filters.append(filter)
        else:
            filters.append(_build_term(key, value))
    
    print("filters: {0}".format(filters))
    
    return filters

    