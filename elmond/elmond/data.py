from util import *
from werkzeug.exceptions import BadRequest, NotImplemented
from filters import build_time_filter
import re

DEFAULT_RESULT_LIMIT=1000
MAX_RESULT_LIMIT=10000
#TODO: DELETE THIS
SUPPORTED_SUMMARIES = {
    "base": True,
    "statistics": True
}
DATA_FIELD_MAP = {
    "histogram-owdelay/base": "result.latency.histogram",
    "histogram-owdelay/statistics": "result.latency",
    "histogram-ttl/base": "result.ttl.histogram",
    "histogram-ttl/statistics": "result.ttl",
    "histogram-rtt/base": "result.rtt.histogram",
    "histogram-rtt/statistics": "result.rtt",
    "packet-count-lost/base": "result.packets.lost",
    "packet-count-lost-bidir/base": "result.packets.lost",
    "packet-count-sent/base": "result.packets.sent",
    "packet-duplicates/base": "result.packets.duplicated",
    "packet-duplicates-bidir/base": "result.packets.duplicated",
    "packet-loss-rate/base": "result.packets.loss",
    "packet-loss-rate-bidir/base": "result.packets.loss",
    "packet-reorders/base": "result.packets.reordered",
    "packet-reorders-bidir/base": "result.packets.reordered",
    "packet-retransmits/base": "result.retransmits",
    "packet-retransmits-subintervals/base": "result.intervals.json",
    "packet-trace/base": "result.json",
    "packet-trace-multi/base": "result.json",
    "path-mtu/base": "result.mtu",
    "streams-packet-retransmits/base": "result.intervals.json",
    "streams-packet-retransmits-subintervals/base": "result.intervals.json",
    "streams-throughput/base": "result.intervals.json",
    "streams-throughput-subintervals/base": "result.intervals.json",
    "throughput/base": "result.throughput_bits",
    "throughput-subintervals/base": "result.intervals.json",
    "time-error-estimates/base": "result.max_clock_error"
}

log = logging.getLogger('elmond')

def _build_esmond_histogram(elastic_histo):
    values = elastic_histo.get("values", [])
    counts = elastic_histo.get("counts", [])
    #make sure same length
    num_buckets = len(values)
    if  num_buckets != len(counts):
        return None
    #build new type
    esmond_histo = {}
    for i in range(num_buckets):
        try:
            esmond_histo[str(values[i])] = int(counts[i])
        except ValueError as e:
            return None
    
    return esmond_histo

def _extract_result_field(key, result):
    key_parts = key.split('.')
    #pop off result at beginning
    key_parts.pop(0)
    curr_field = result
    for key_part in key_parts:
        #pull out the field
        try:
            curr_field = curr_field.get(key_part, None)
        except:
            #handle error because of unexpected object structure
            log.error("Error while extracting field {0}.".format(key_part))
            return None
        #if didn't find field, then return None
        if curr_field is None:
            return None
    
    return curr_field

def _extract_result_stats(key, result):
    field = _extract_result_field(key, result)
    if field is None:
        return None
    
    return {
        "maximum": field.get("max", None),
        "mean": field.get("mean", None),
        "median": field.get("median", None),
        "minimum": field.get("min", None),
        "mode": field.get("mode", None),
        "percentile-25": field.get("p_25", None),
        "percentile-75": field.get("p_75", None),
        "percentile-95": field.get("p_95", None),
        "standard-deviation": field.get("stddev", None),
        "variance": field.get("variance", None)
    }
    
def _extract_result_subintervals(key, result, event_type):
    #extract interval field
    intervals = _extract_result_field(key, result)
    if intervals is None:
        return None
    #figure out which key we are looking for by taking advantage of structure of
    # subinterval event type name
    interval_event_type = event_type
    interval_event_type = re.sub(r'^streams-', "", interval_event_type)
    interval_event_type = re.sub(r'-subintervals$', "", interval_event_type)
    interval_key = DATA_FIELD_MAP.get("{0}/base".format(interval_event_type), None)
    if interval_key is None:
        return None
    else:
        #kinda a hack, but works
        interval_key = re.sub("_", "-", interval_key)
    
    esmond_intervals = []
    for interval in intervals:
        if interval.get("summary", None):
            start = interval["summary"].get("start", None)
            end = interval["summary"].get("end", None)
            if start is None or end is None:
                continue
            duration = end - start
            val = _extract_result_field(interval_key, interval["summary"])
            if val is None:
                continue
            esmond_intervals.append({ "start": start, "duration": duration, "val": val})

    return esmond_intervals

class EsmondData:

    def __init__(self, es):
        self.es = es
    
    def fetch(self, metadata_key, event_type, summary_type, summary_window, q={}):
        #right now we can't handle summaries
        log.debug("{0} {1}".format(summary_type, summary_window))
        #convert summary window to int
        try:
            summary_window = int(summary_window)
        except ValueError as e:
            raise BadRequest("Summary window must be an int")
        if summary_type not in SUPPORTED_SUMMARIES or summary_window != 0:
            raise NotImplemented("Currently only base and statistics summaries with window 0 are supported")
        
        #handle limit and offset
        result_size = DEFAULT_RESULT_LIMIT
        result_offset = 0
        if q.get(LIMIT_FILTER, None):
            try:
                result_size = int(q[LIMIT_FILTER])
            except ValueError:
                raise BadRequest("{0} parameter must be an integer".format(LIMIT_FILTER))
        if q.get(OFFSET_FILTER, None):
            try:
                result_offset = int(q[OFFSET_FILTER])
            except ValueError:
                raise BadRequest("{0} parameter must be an integer".format(OFFSET_FILTER))
        if result_size > MAX_RESULT_LIMIT:
            raise BadRequest("{0} parameter cannot exceed {1}".format(LIMIT_FILTER, MAX_RESULT_LIMIT))

        #data query
        dsl = {
            "size": result_size,
            "from": result_offset,
            "_source": ["pscheduler.start_time"],
            "sort": [
              {
                "pscheduler.start_time": {
                  "order": "asc"
                }
              }
            ], 
            "query": {
              "bool": {
                "filter": [
                  {
                    "term": {
                      "pscheduler.test_checksum": metadata_key
                    }
                  }
                ]
              }
            }
        }
        
        #handle time filters
        time_filter = build_time_filter(q)
        if time_filter:
            dsl["query"]["bool"]["filter"].append(time_filter)
        
        #limit fields returned
        dfm_key = "{0}/{1}".format(event_type, summary_type)
        raw_type = True
        if dfm_key in DATA_FIELD_MAP:
            raw_type = False
            if isinstance(DATA_FIELD_MAP[dfm_key], list):
                dsl["_source"].extend(DATA_FIELD_MAP[dfm_key])
            else:
                dsl["_source"].append(DATA_FIELD_MAP[dfm_key])
        elif event_type == "pscheduler-raw":
            dsl["_source"].append("result.*")
        else:
            raise BadRequest("Unrecognized event type {0}".format(event_type))
        
        #exec query
        res = self.es.search(index="pscheduler_*", body=dsl)
        hits = res.get("hits", {}).get("hits", [])
        
        #parse results
        data = []
        for hit in hits:
            #get time stamp
            ts = hit.get("_source", {}).get("pscheduler", {}).get("start_time", None) 
            result = hit.get("_source", {}).get("result", None)
            if not ts or not result:
                continue
            datum = { "ts": datestr_to_timestamp(ts) }
            #get value - event type specific. 
            # Note: right now it either spits out an empty string or just gives raw results for unsupported event types
            if raw_type:
                datum["val"] = result
            elif event_type.startswith("histogram-") and summary_type == "statistics":
                datum["val"] = _extract_result_stats(DATA_FIELD_MAP[dfm_key], result)
            elif event_type.startswith("histogram-"):
                hist = _extract_result_field(DATA_FIELD_MAP[dfm_key], result)
                if not hist:
                    continue
                datum["val"] = _build_esmond_histogram(hist)
            elif event_type.startswith("streams") and event_type.endswith("subintervals"):
                pass
            elif event_type.startswith("streams"):
                pass
            elif event_type.endswith("subintervals"):
                datum["val"] = _extract_result_subintervals(DATA_FIELD_MAP[dfm_key], result, event_type)
            else:
                #extract from the map
                datum["val"] = _extract_result_field(DATA_FIELD_MAP[dfm_key], result)
            
            #if we didn't find anything continue - esmond never has a null point (i think)
            if datum["val"] is None:
                continue
            
            #add to list of data
            data.append(datum)    

        return data

