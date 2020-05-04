import dateutil.parser
import logging
import re
from filters import build_filters
from flask import current_app as app
from summaries import DEFAULT_SUMMARIES
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from util import *

DEFAULT_RESULT_LIMIT=1000
MAX_RESULT_LIMIT=10000

log = logging.getLogger('elmond')

class EsmondMetadata:

    def __init__(self, es):
        self.es = es
    
    def _get_next_link(self, request_url, result_size, result_offset, metadata_count):
        if (result_size + result_offset) >= metadata_count:
            return None
        new_offset = result_size + result_offset
        new_limit = result_size
        if (new_offset + new_limit) > metadata_count and new_offset < metadata_count:
            #if someone specifies an offset too big just ignore it
            new_limit =   metadata_count - new_offset
             
        url_parts = list(urlparse(request_url))
        query = dict(parse_qsl(url_parts[4]))
        query.update({ "limit": new_limit, "offset": new_offset})
        url_parts[4] = urlencode(query)
        
        return urlunparse(url_parts)
    
    def _get_prev_link(self, request_url, result_size, result_offset, metadata_count):
        if result_offset == 0:
            return None
        new_offset = result_offset - result_size
        new_limit = result_size
        if result_size > result_offset:
            new_offset = 0
            new_limit = result_offset
             
        url_parts = list(urlparse(request_url))
        query = dict(parse_qsl(url_parts[4]))
        query.update({ "limit": new_limit, "offset": new_offset})
        url_parts[4] = urlencode(query)
        
        return urlunparse(url_parts)
    
    def _get_md_url(self, request_url, md_key):
        url_parts = list(urlparse(request_url))
        url_parts[2] = re.sub(r'/$', "", url_parts[2])
        if not url_parts[2].endswith(md_key):
            url_parts[2] = "{0}/{1}".format(url_parts[2], md_key)
        return urlunparse(url_parts)
        
    def search(self, q=None, request_url=None, paginate=False):
        #get pagination options
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

        #base search
        dsl = {
            "size": 0,
            "aggs" : {
                "tests_total_count" : {
                  "cardinality": {
                    "field": "pscheduler.test_checksum.keyword"
                  }
                },
                "tests" : {
                    "terms" : { 
                      "field" : "pscheduler.test_checksum.keyword"
                    },
                    "aggs": {
                      "test_params": {
                        "top_hits": {
                          "size": 1,
                          "sort": [ { "pscheduler.start_time": { "order": "desc" } } ],
                          "_source": ["test.*", "meta.*", "pscheduler.*", "reference.*"]
                        }
                      },
                      "latest_test": {
                        "max": {
                          "field":"pscheduler.start_time"
                        }
                      },
                      "sorted_test": {
                        "bucket_sort": {
                          "sort": [
                            {"latest_test": {"order": "desc"}}
                          ],
                          "size": result_size,
                          "from": result_offset
                        }
                      }
                    }
                }
            }
        }
        
        #build seatch filters
        filters = build_filters(q)
        if len(filters) > 0:
            dsl["query"] = {
                "bool": {
                    "filter": filters
                }
            }

        #Get list of tests
        res = self.es.search(index="pscheduler_*", body=dsl)
        
        #format JSON
        metadata=[]
        buckets = res.get("aggregations",{}).get("tests",{}).get("buckets",[])
        for bucket in buckets:
            #metadata key
            md_obj={
                'metadata-key': bucket.get("key"),
                'uri': build_uri(bucket.get("key"))
            }
            
            #extract meta, test and schedule 
            hits = bucket.get("test_params",{}).get("hits",{}).get("hits", [])
            if len(hits) == 0:
                continue
            hit=hits[0].get("_source",{})
            meta=hit.get("meta",{})
            test=hit.get("test",{})
            pscheduler=hit.get("pscheduler",{})
            reference=hit.get("reference",{})
            
            #parse measurement-agent
            observer_ip = meta.get("observer", {}).get("ip", None)
            if observer_ip:
                md_obj['measurement-agent'] = observer_ip
            else:
                continue
            
            #parse source and dest
            source_ip = meta.get("source", {}).get("ip", None)
            dest_ip = meta.get("destination", {}).get("ip", None)
            if source_ip and dest_ip:
                md_obj['subject-type'] = "point-to-point"
                md_obj['source'] = source_ip
                md_obj['destination'] = dest_ip
            elif source_ip:
                md_obj['subject-type'] = "network-element"
                md_obj['source'] = source_ip
            elif observer_ip:
                md_obj['subject-type'] = "network-element"
                md_obj['source'] = observer_ip
            else:
                continue
                
            #parse pschedule object
            tool=pscheduler.get("tool", None)
            if tool:
                md_obj['tool-name'] = "pscheduler/{0}".format(tool)
            else:
                continue
            #this matches the old esmond archive behavior, though not sure it is
            #the desired value since includes scheduling fluff time
            md_obj['time-duration'] = pscheduler.get("duration", None)
            
            #parse test parameters
            test_type = test.get("type", None)
            md_obj['pscheduler-test-type'] = test_type
            spec = test.get("spec", None)
            if not spec:
                continue
            md_obj['input-source'] = spec.get("source", None)
            if not md_obj['input-source']:
                #this matches old behavior, though not sure it is desired
                md_obj['input-source'] = md_obj['measurement-agent']
            if spec.get("dest", None):
                md_obj['input-destination'] = spec["dest"]
            
            #add type specific parameters
            field_parser = None
            if test_type == 'throughput':
                field_parser = EsmondThroughputMetadataFieldParser()
            elif test_type == 'latency' or test_type == 'latencybg':
                field_parser = EsmondLatencyMetadataFieldParser()
            elif test_type == 'disk-to-disk':
                field_parser = EsmondDiskToDiskMetadataFieldParser()
            elif test_type == 'trace':
                field_parser = EsmondTraceMetadataFieldParser()
            elif test_type == 'rtt':
                field_parser = EsmondRttMetadataFieldParser()
            else:
                field_parser = EsmondRawMetadataFieldParser(test_type)
                
            if pscheduler.get("added", None):
                time_added = int(dateutil.parser.parse(pscheduler['added']).timestamp())
                print("time_added={0}".format(time_added))
            
            field_parser.parse(spec, md_obj, reference=reference, md_key=md_obj['metadata-key'], time_added=time_added)
            if request_url:
                md_obj['url'] = self._get_md_url(request_url, md_obj['metadata-key'])
            metadata.append(md_obj)
        
        #add the metadata count and pagination fields to first element. this is how esmond did it.
        metadata_count = res.get("aggregations", {}).get("tests_total_count",{}).get("value",0)
        
        if paginate and metadata_count != 0 and len(metadata) > 0:
            metadata[0]["metadata-count-total"] = metadata_count
            metadata[0]["metadata-previous-page"] = self._get_prev_link(request_url, result_size, result_offset, metadata_count)
            metadata[0]["metadata-next-page"] = self._get_next_link(request_url, result_size, result_offset, metadata_count)
        
        return metadata
        
class EsmondMetadataFieldParser:
    field_map={}
    
    def parse(self, test_spec, target, reference=None, md_key=None, time_added=None):
        #map fields
        for field in self.field_map:
            if field in test_spec:
                target[self.field_map[field]] = test_spec[field]
        #add fields without direct mapping
        self._add_additional_metadata(test_spec, target)
        #add reference metadata
        ## NOTE: reference is not part of checksum, so if not filtering on 
        # reference you may not see the right reference fields
        if reference:
            for field in reference:
                if field.startswith('_'):
                    continue
                key = "pscheduler-reference-%s" % (field)
                val = reference[field]
                self._parse_metadata_field(key, val, target)
        #add event types 
        target['event-types'] = []
        for et in self._get_event_types(test_spec):
            self.__add_event_type(et, target, md_key=md_key, time_added=time_added)
        self.__add_event_type('pscheduler-run-href', target, md_key=md_key, time_added=time_added)
        self.__add_event_type('pscheduler-raw', target, md_key=md_key, time_added=time_added)
        
    def _parse_metadata_field(self, key, val, target):
        if type(val) is list:
            for (i, v) in enumerate(val):
                k = "%s-%d" % (key, i)
                target[k] = v
        elif type(val) is dict:
            for sub_key in val:
                if sub_key.startswith('_'):
                    continue
                k = "%s-%s" % (key, sub_key)
                self._parse_metadata_field(k, val[sub_key], target)
        else:
            target[key] = val
     
    def __add_event_type(self, event_type, target, md_key=None, time_added=None):
        et = { "event-type": event_type }
        if md_key:
            et['base-uri'] = build_uri(md_key, event_type)
            
        if time_added:
            et['time-updated'] = time_added
        
        #Load summaries from config
        et_summary_map = app.config.get('ELMOND', {}).get('SUMMARIES', None)
        if not et_summary_map:
            et_summary_map = DEFAULT_SUMMARIES
        #Map summaries to event type
        if event_type in et_summary_map:
            et["summaries"] = []
            for summary in et_summary_map[event_type]:
                summ_obj = {
                    "event-type":   summary["event-type"],
                    "summary-window":   summary["summary-window"],
                    "summary-type":   summary["summary-type"]
                }
                if md_key:
                    summ_obj["uri"] = build_uri(
                        md_key, 
                        event_type=event_type, 
                        summary_type=summary["summary-type"], 
                        summary_window=summary["summary-window"]
                    )
                et["summaries"].append(summ_obj)
        target['event-types'].append(et)
        
    def _get_event_types(self, test_spec):
        return []
    
    def _add_additional_metadata(self, test_spec, target):
        pass
        

class EsmondThroughputMetadataFieldParser(EsmondMetadataFieldParser):
    field_map = {
        'tos': 'ip-tos',
        'dscp': 'ip-dscp',
        'buffer-length': 'bw-buffer-size',
        'parallel': 'bw-parallel-streams',
        'bandwidth': 'bw-target-bandwidth',
        'window-size': 'tcp-window-size',
        'dynamic-window-size': 'tcp-dynamic-window-size',
        'mss': 'tcp-max-segment-size',
        'omit': 'bw-ignore-first-seconds'
    }
    
    def _add_additional_metadata(self, test_spec, target):
        if 'udp' in test_spec and test_spec['udp']:
            target['ip-transport-protocol'] = 'udp'
        else:
            target['ip-transport-protocol'] = 'tcp'
    
    def _get_event_types(self, test_spec):
        event_types = [
            'failures',
            'throughput',
            'throughput-subintervals',
        ]
        if 'parallel' in test_spec and test_spec['parallel'] > 1:
            event_types.append('streams-throughput')
            event_types.append('streams-throughput-subintervals')
        if 'udp' in test_spec and test_spec['udp']:
            event_types.append('packet-loss-rate')
            event_types.append('packet-count-lost')
            event_types.append('packet-count-sent')
        else:
            event_types.append('packet-retransmits')
            event_types.append('packet-retransmits-subintervals')
            if 'parallel' in test_spec and test_spec['parallel'] > 1:
                event_types.append('streams-packet-retransmits')
                event_types.append('streams-packet-retransmits-subintervals')
        return event_types

class EsmondLatencyMetadataFieldParser(EsmondMetadataFieldParser):
    field_map = {
        "packet-count":  "sample-size", 
        "bucket-width":  "sample-bucket-width", 
        "packet-interval": "time-probe-interval", 
        "packet-timeout": "time-probe-timeout", 
        "ip-tos": "ip-tos", 
        "flip": "mode-flip", 
        "packet-padding": "ip-packet-padding", 
        "single-participant-mode": "mode-single-participant"
    }
    
    def _get_event_types(self, test_spec):
        event_types = [
            'failures',
            'packet-count-sent',
            'histogram-owdelay',
            'histogram-ttl',
            'packet-duplicates',
            'packet-loss-rate',
            'packet-count-lost',
            'packet-reorders',
            'time-error-estimates'
        ]
        return event_types

class EsmondTraceMetadataFieldParser(EsmondMetadataFieldParser):
    field_map = {
        "algorithm":   'trace-algorithm',
        "first-ttl":   'trace-first-ttl',
        "fragment":    'ip-fragment',
        "hops":        'trace-max-ttl',
        "length":      'ip-packet-size',
        "probe-type":  'ip-transport-protocol',
        "queries":     'trace-num-queries',
        "tos":         'ip-tos'
    }
    
    def _add_additional_metadata(self, test_spec, target):
        if test_spec.get("sendwait", None):
            target["time-probe-interval"] = iso8601_to_seconds(test_spec["sendwait"])
        if test_spec.get("wait", None):
            target["time-test-timeout"] = iso8601_to_seconds(test_spec["wait"])
            
    def _get_event_types(self, test_spec):
        event_types = [
            'failures',
            'packet-trace',
            'path-mtu'
        ]
        if "paris-traceroute" == test_spec.get('algorithm', ''):
            event_types.append('packet-trace-multi')
            
        return event_types

class EsmondRttMetadataFieldParser(EsmondMetadataFieldParser):
    field_map = {
        "count": "sample-size",
        "flowlabel": "ip-packet-flowlabel",
        "tos": "ip-tos",
        "length": "ip-packet-size",
        "ttl": "ip-ttl",
    }
    def _get_event_types(self, test_spec):
        event_types = [
            'failures',
            'packet-count-sent',
            'histogram-rtt',
            'histogram-ttl-reverse',
            'packet-duplicates-bidir',
            'packet-loss-rate-bidir',
            'packet-count-lost-bidir',
            'packet-reorders-bidir'
        ]
        return event_types
    
    def _add_additional_metadata(self, test_spec, target):
        if test_spec.get("interval", None):
            target["time-probe-interval"] = iso8601_to_seconds(test_spec["interval"])
        if test_spec.get("timeout", None):
            target["time-test-timeout"] = iso8601_to_seconds(test_spec["timeout"])
        if test_spec.get("deadline", None):
            target["time-probe-timeout"] = iso8601_to_seconds(test_spec["deadline"])


class EsmondRawMetadataFieldParser(EsmondMetadataFieldParser):
    
    def __init__(self, test_type):
        self.test_type = test_type
    
    def _add_additional_metadata(self, test_spec, target):
        for field in test_spec:
            key = "pscheduler-%s-%s" % (self.test_type, field)
            val = test_spec[field]
            self._parse_metadata_field(key, val, target)

class EsmondDiskToDiskMetadataFieldParser(EsmondRawMetadataFieldParser):
    field_map = {
        'parallel': 'bw-parallel-streams',
    }

    def __init__(self):
        super().__init__('disk-to-disk')
    
    def _get_event_types(self, test_spec):
        event_types = [
            'failures',
            'throughput'
        ]
        return event_types

