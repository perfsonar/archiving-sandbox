from util import *
from werkzeug.exceptions import BadRequest, NotImplemented
from filters import build_time_filter

DEFAULT_RESULT_LIMIT=1000
MAX_RESULT_LIMIT=10000
DATA_FIELD_MAP = {
    "throughput": "result.throughput_bits"
}
log = logging.getLogger('elmond')


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
        if summary_type != "base" or summary_window != 0:
            raise NotImplemented("Currently only base summaries with window 0 are supported")
        
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
        if event_type in DATA_FIELD_MAP:
            dsl["_source"].append(DATA_FIELD_MAP[event_type])
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
            #get value - event type specific
            if event_type == "throughput":
                if "throughput_bits" in result:
                    datum["val"] = result["throughput_bits"]
                else:
                    continue
            else:
                datum["val"] = result
            data.append(datum)    

        return data

