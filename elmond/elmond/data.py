from util import *
from werkzeug.exceptions import BadRequest, NotImplemented
from filters import build_time_filter

DEFAULT_RESULT_LIMIT=1000
MAX_RESULT_LIMIT=10000
#TODO: DELETE THIS
SUPPORTED_SUMMARIES = {
    "base": True,
    "statistics": True
}
DATA_FIELD_MAP = {
    "throughput/base": "result.throughput_bits",
    "histogram-owdelay/base": "result.latency.histogram",
    "histogram-owdelay/statistics": [
        "result.latency.max",
        "result.latency.mean",
        "result.latency.median",
        "result.latency.min",
        "result.latency.mode",
        "result.latency.p_25",
        "result.latency.p_75",
        "result.latency.p_95",
        "result.latency.stddev",
        "result.latency.variance"
    ]
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
        if dfm_key in DATA_FIELD_MAP:
            if isinstance(DATA_FIELD_MAP[dfm_key], list):
                dsl["_source"].extend(DATA_FIELD_MAP[dfm_key])
            else:
                dsl["_source"].append(DATA_FIELD_MAP[dfm_key])
        else:
            dsl["_source"].append("result.*")
        
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
            if event_type == "throughput":
                if "throughput_bits" in result:
                    datum["val"] = result["throughput_bits"]
                else:
                    continue
            elif event_type == "histogram-owdelay" and summary_type == "statistics":
                if "latency" in result:
                    datum["val"] = {
                        "maximum": result["latency"].get("max", None),
                        "mean": result["latency"].get("mean", None),
                        "median": result["latency"].get("median", None),
                        "minimum": result["latency"].get("min", None),
                        "mode": result["latency"].get("mode", None),
                        "percentile-25": result["latency"].get("p_25", None),
                        "percentile-75": result["latency"].get("p_75", None),
                        "percentile-95": result["latency"].get("p_95", None),
                        "standard-deviation": result["latency"].get("stddev", None),
                        "variance": result["latency"].get("variance", None)
                    }
                else:
                    continue
            elif event_type == "histogram-owdelay":
                if "latency" in result and "histogram" in result["latency"]:
                    datum["val"] = _build_esmond_histogram(result["latency"]["histogram"])
                    if datum["val"] is None:
                        continue
                else:
                    continue
            else:
                datum["val"] = result
            data.append(datum)    

        return data

