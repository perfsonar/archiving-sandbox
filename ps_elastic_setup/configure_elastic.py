import requests
import argparse
import os
import re
import json
import sys 
import time

DEFAULT_ELASTIC_URL="http://localhost:9200"
DEFAULT_CONFIG_DIR="."

def init_index(template, elastic_url):
    # Create an initial index if one does not exist
    index_pattern=template['index_patterns'][0]
    
    # Check if exists
    url = "{0}/{1}/_ilm/explain".format(elastic_url, index_pattern)
    try:
        print("type=init_index action=get.start url={0}".format(url))
        r = requests.get(url=url)
        r.raise_for_status()
        print("type=init_index action=get.end url={0} status={1} elastic_reponse={2}".format(url, r.status_code, r.text))
        if len(r.json().get("indices", {})) > 0:
            #already has indices, no need to init
            return
    except:
        print("type=init_index action=get.error url={0} msg={1}".format(url, sys.exc_info()))
    
    # Create index
    index_alias=template["settings"]["index.lifecycle.rollover_alias"]
    index_name="{0}-000001".format(index_alias)
    url = "{0}/{1}".format(elastic_url, index_name)
    try:
        print("type=init_index action=put.start url={0}".format(url))
        r = requests.put(url=url, json={"aliases": {index_alias: {"is_write_index": True}}})
        r.raise_for_status()
        print("type=init_index action=put.end url={0} status={1} elastic_reponse={2}".format(url, r.status_code, r.text))
    except:
        print("type=init_index action=put.error url={0} msg={1}".format(url, sys.exc_info()))
        
def load_from_file(type, elastic_path, config_dir=DEFAULT_CONFIG_DIR, elastic_url=DEFAULT_ELASTIC_URL, post_func=None):
    dir="{0}/{1}".format(config_dir, type)
    with os.scandir(dir) as dir_entries:
         for dir_entry in dir_entries:
            if dir_entry.is_file() and dir_entry.name.endswith(".json"):
                policy_name = re.sub(r'\.json$', "", dir_entry.name)
                url = "{0}/{1}/{2}".format(elastic_url, elastic_path, policy_name)
                print("type={0} action=create.start file={1} url={2}".format(type, dir_entry.path, url))
                try:
                    with open(dir_entry.path) as policy_file:
                        policy = json.load(policy_file)
                    r = requests.put(url=url, json=policy)
                    r.raise_for_status() #raise error if failed
                    print("type={0} action=create.end file={1} url={2} status={3} elastic_reponse={4}".format(type, dir_entry.path, url, r.status_code, r.text))
                    if post_func:
                        post_func(policy, elastic_url)
                except:
                    print("type={0} action=create.error file={1} url={2} msg={3}".format(type, dir_entry.name, url, r.text))

#Parse command-line args
parser = argparse.ArgumentParser(description='Configure ElasticSearch for perfSONAR')
parser.add_argument('-c', dest='config_dir', default=DEFAULT_CONFIG_DIR, type=str, help='The configuration directory')
parser.add_argument('-u', dest='elastic_url', default=DEFAULT_ELASTIC_URL, type=str, help='The elastic URL.')
parser.add_argument('--max-retries', dest='max_retries', default=120, type=int, help='Number of times to try to connect to elastic')
parser.add_argument('--retry-wait', dest='retry_wait', default=1, type=int, help='Seconds to sleep between retries')

args = parser.parse_args()

#0. Wait for elastic to come up
retries = 0
connected=False
while retries < args.max_retries and not connected:
    retries += 1
    try:
        r = requests.get(url=args.elastic_url)
        r.raise_for_status()
        connected=True
    except:
        print("Unable to connect to elastic. Will retry again in {0} second(s).".format(args.retry_wait))
        time.sleep(args.retry_wait)
if not connected:
    print("Unable to connect to elasticsearch after {0} attempts.".format(args.max_retries))
    sys.exit(1)

#1. Create ILM policies
load_from_file("ilm", "_ilm/policy", config_dir=args.config_dir, elastic_url=args.elastic_url)
#2. Create index templates for rollups so they have ILM - also initialize first index
#load_from_file("rollup_index_templates", "_template", config_dir=args.config_dir, elastic_url=args.elastic_url, post_func=init_index)
#3. Create rollups (require index to rollup to already exist) 
#load_from_file("rollups", "_rollup/job")
