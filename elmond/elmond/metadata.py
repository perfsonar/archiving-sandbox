import logging
            
class EsmondMetadata:

    def __init__(self, es):
        self.es = es
    
    def search(self):
        #todo: add rest of test types
        #todo: parameter handling
        #todo: calculate index names based on time
        #todo: errorhandling
        #todo: pagination
        #todp: add event types
        #todp: add summaries
        #todo: sort newest to oldest
        
        #Get list of tests
        res = self.es.search(index="pscheduler_*", body={
            "size": 0,
            "aggs" : {
                "tests" : {
                    "terms" : { 
                      "field" : "pscheduler.test_checksum.keyword"
                    },
                    "aggs": {
                      "test_params": {
                        "top_hits": {
                          "size": 1,
                          "_source": ["test.*", "meta.*", "pscheduler.*", "reference.*"]
                        }
                      }
                    }
                }
            }
        })
        
        #format JSON
        metadata=[]
        buckets = res.get("aggregations",{}).get("tests",{}).get("buckets",[])
        for bucket in buckets:
            #metadata key
            md_obj={
                'metadata-key': bucket.get("key")
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
            else:
                continue
            
            #parse measurement-agent
            observer_ip = meta.get("observer", {}).get("ip", None)
            if observer_ip:
                md_obj['measurement-agent'] = observer_ip
            else:
                continue
                
            #parse pschedule object
            tool=pscheduler.get("tool", None)
            if tool:
                md_obj['tool-name'] = tool
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
            md_obj['input-destination'] = spec.get("dest", None)
            
            #add type specific parameters
            field_parser = None
            if test_type == 'throughput':
                field_parser = EsmondThroughputMetadataFieldParser()
            elif test_type == 'latency' or test_type == 'latencybg':
                field_parser = EsmondLatencyMetadataFieldParser()
            
            field_parser.parse(spec, md_obj, reference=reference)
            metadata.append(md_obj)
        
        return metadata
        
class EsmondMetadataFieldParser:
    def parse(self, test_spec, target, reference=None):
        #map fields
        for field in self.field_map:
            if field in test_spec:
                target[self.field_map[field]] = test_spec[field]
        #add fields without direct mapping
        self._add_additional_metadata(test_spec, target)
        #add reference metadata
        ## NOTE: reference is not part of checksum, so if not filtering on 
        # checksum you may not see the reference fields
        if reference:
            for field in reference:
                if field.startswith('_'):
                    continue
                key = "pscheduler-reference-%s" % (field)
                val = reference[field]
                self.__parse_metadata_field(key, val, target)

    def __parse_metadata_field(self, key, val, target):
        if type(val) is list:
            for (i, v) in enumerate(val):
                k = "%s-%d" % (key, i)
                target[k] = v
        elif type(val) is dict:
            for sub_key in val:
                if sub_key.startswith('_'):
                    continue
                k = "%s-%s" % (key, sub_key)
                self.__parse_metadata_field(k, val[sub_key], target)
        else:
            target[key] = val
            
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