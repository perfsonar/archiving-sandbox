'''
SUMMARY_TYPES: The supported summaries. The key is the name as it appears in the URL
(usually plural form) and the value is the name as it appears in JSON.
'''
SUMMARY_TYPES = {
    "base": "base",
    "aggregations": "aggregation",
    "statistics": "statistics",
    "averages": "average"
}

'''
INVERSE_SUMMARY_TYPES: Same as SUMMARY_TYPES with the key and values swapped
'''
INVERSE_SUMMARY_TYPES = {v:k for k,v in SUMMARY_TYPES.items()}

#TODO: Make configurable
DEFAULT_SUMMARIES = {
    "throughput": [
        {
            "summary-window":   86400,
            "event-type":   "throughput",
            "summary-type":   "average",
        },
    ],
    "packet-loss-rate": [
        {
            "summary-window":   300,
            "event-type":   "packet-loss-rate",
            "summary-type":   "aggregation",
        },
        {
            "summary-window":   3600,
            "event-type":   "packet-loss-rate",
            "summary-type":   "aggregation",
        },
        {
            "summary-window":   86400,
            "event-type":   "packet-loss-rate",
            "summary-type":   "aggregation",
        },
    ],
    "packet-count-sent": [
        {
            "summary-window":   300,
            "event-type":   "packet-count-sent",
            "summary-type":   "aggregation",
        },
        {
            "summary-window":   3600,
            "event-type":   "packet-count-sent",
            "summary-type":   "aggregation",
        },
        {
            "summary-window":   86400,
            "event-type":   "packet-count-sent",
            "summary-type":   "aggregation",
        },
    ],
    "packet-count-lost": [
        {
            "summary-window":   300,
            "event-type":   "packet-count-lost",
            "summary-type":   "aggregation",
        },
        {
            "summary-window":   3600,
            "event-type":   "packet-count-lost",
            "summary-type":   "aggregation",
        },
        {
            "summary-window":   86400,
            "event-type":   "packet-count-lost",
            "summary-type":   "aggregation",
        },
    ],
    "packet-count-lost-bidir": [
        {
            "summary-window":   300,
            "event-type":   "packet-count-lost-bidir",
            "summary-type":   "aggregation",
        },
        {
            "summary-window":   3600,
            "event-type":   "packet-count-lost-bidir",
            "summary-type":   "aggregation",
        },
        {
            "summary-window":   86400,
            "event-type":   "packet-count-lost-bidir",
            "summary-type":   "aggregation",
        },
    ],
    "histogram-owdelay": [
        {
            "summary-window":   0,
            "event-type":   "histogram-owdelay",
            "summary-type":   "statistics",
        },
        {
            "summary-window":   300,
            "event-type":   "histogram-owdelay",
            "summary-type":   "statistics",
        },
        {
            "summary-window":   3600,
            "event-type":   "histogram-owdelay",
            "summary-type":   "statistics",
        },
        {
            "summary-window":   86400,
            "event-type":   "histogram-owdelay",
            "summary-type":  "statistics",
        },
    ],
    "packet-loss-rate-bidir":[
        {
            "summary-window":   300,
            "event-type":   "packet-loss-rate-bidir",
            "summary-type":   "aggregation",
        },
        {
            "summary-window":   3600,
            "event-type":   "packet-loss-rate-bidir",
            "summary-type":   "aggregation",
        },
        {
            "summary-window":   86400,
            "event-type":   "packet-loss-rate-bidir",
            "summary-type":   "aggregation",
        },
    ],
    "histogram-rtt": [
        {
            "summary-window":   0,
            "event-type":   "histogram-rtt",
            "summary-type": "statistics",
        },
        {
            "summary-window":   300,
            "event-type":   "histogram-rtt",
            "summary-type":   "statistics",
        },
        {
            "summary-window":   3600,
            "event-type":   "histogram-rtt",
            "summary-type":  "statistics",
        },
        {
            "summary-window":   86400,
            "event-type":   "histogram-rtt",
            "summary-type": "statistics",
        }
    ],
}