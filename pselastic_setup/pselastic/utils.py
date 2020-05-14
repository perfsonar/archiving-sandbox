import requests
import argparse
import os
import re
import json
import sys 
import time
import logging
from requests.auth import HTTPBasicAuth

DEFAULT_ELASTIC_URL="http://localhost:9200"
DEFAULT_CONFIG_DIR="./conf.d"

class PSElasticUtil:

    def __init__(self):
        self.resource = None
        self.log = None
        self.auth = None
        self.valid_actions = []
        self.subactions=None

    '''
    Loads a set of JSON files from a directory and sends them to elastic via HTTP.
    action: the subdirectory under the resources directory where JSON files live
    url_path_prefix: the part of the path before the resource name. URL is built {elastic_url}/{url_path_prefix}/{filename before .json}/{url_path_suffix}
    url_path_suffix: the part of the path after the resource name. URL is built {elastic_url}/{url_path_prefix}/{filename before .json}/{url_path_suffix}
    config_dir: directory where resource directory lives
    elastic_url: base url of elastic
    pre_func: a function to be executed before performing main elastic operation for each file. If function returns false, will skip to next file
    post_func: a function to be run after a successful run of an operation
    '''
    def load_from_file(self, 
                        action,
                        url_path_prefix=None,
                        url_path_suffix=None,
                        config_dir=DEFAULT_CONFIG_DIR,
                        elastic_url=DEFAULT_ELASTIC_URL,
                        pre_func=None,
                        post_func=None,
                        http_method=requests.put
                    ):
        #Iterate through items in the config_dir/resource/action directory
        dir="{0}/{1}/{2}".format(config_dir, self.resource, action)
        with os.scandir(dir) as dir_entries:
             for dir_entry in dir_entries:
                #Skip unless it is a file ending in .json
                if dir_entry.is_file() and dir_entry.name.endswith(".json"):
                    policy_name = re.sub(r'\.json$', "", dir_entry.name)
                    if self.subactions and policy_name not in self.subactions:
                        continue
                    #If __ at end of name with some text after, the replace with * 
                    policy_name = re.sub(r'__.+$', "*", policy_name)
                    #Build the elastic URL
                    url = elastic_url
                    if url_path_prefix:
                        url = "{0}/{1}".format(url, url_path_prefix)
                    url = "{0}/{1}".format(url, policy_name)
                    if url_path_suffix:
                        url = "{0}/{1}".format(url, url_path_suffix)
                    self.log.debug("resource={0} action={1}.start file={2} url={3}".format(self.resource, action, dir_entry.path, url))
                    
                    try:
                        #Open the file and load the JSON
                        with open(dir_entry.path) as policy_file:
                            policy = json.load(policy_file)
                        
                        #Run the pre-function which should tell us if we can perform this operation
                        if pre_func and not pre_func(policy_name, policy, elastic_url):
                            self.log.debug("resource={0} action={1}.end file={2} url={3}".format(self.resource, action, dir_entry.path, url))
                            continue
                        
                        #Send the JSON to the target elastic URL
                        r = http_method(url=url, json=policy, auth=self.auth)
                        r.raise_for_status() #raise error if failed
                        self.log.info("resource={0} action={1}.end file={2} url={3} status={4} elastic_reponse={5}".format(self.resource, action, dir_entry.path, url, r.status_code, r.text))
                        
                        #If there is a post function, do that operation
                        if post_func:
                            post_func(policy_name, policy, elastic_url)
                    except:
                        self.log.error("resource={0} action={1}.error file={2} url={3} msg={4}".format(self.resource, action, dir_entry.name, url, r.text))
    
    def build_arg_parser(self):
        #Parse command-line args
        parser = argparse.ArgumentParser(description='Configure ElasticSearch for perfSONAR')
        parser.add_argument('-c', dest='config_dir', default=DEFAULT_CONFIG_DIR, type=str, help='The configuration directory')
        parser.add_argument('-u', dest='elastic_url', default=None, type=str, help='The elastic URL. Can also be set with PSELASTIC_URL environment variable. Command-line option takes precedence if both present.')
        parser.add_argument('--login-file', dest='elastic_login_file', default=None, type=str, help='A file with one line on format "USER PASSWORD". PSELASTIC_USER and PSELASTIC_PASS environment variables can also set these values. Command-line option takes precedence if both present.')
        parser.add_argument('--log-config', dest='log_config', default=None, type=str, help='A logging configuration file to give to python logging')
        parser.add_argument('--verbose', dest='verbose', action='store_true', help='Give more output')
        parser.add_argument('--max-retries', dest='max_retries', default=0, type=int, help='Number of times to try to connect to elastic')
        parser.add_argument('--retry-wait', dest='retry_wait', default=1, type=int, help='Seconds to sleep between retries')
        parser.add_argument('--periodic', dest='periodic', default=0, type=int, help='Run this action periodically every number of seconds specified.')
        parser.add_argument('action', nargs=1, default=None, type=str, help='The action to perform')
        parser.add_argument('subactions', nargs='*', default=None, type=str, help='An optional list of subactions to perforrm.')
        return parser

    def handle_resource_actions(self, args):
        pass
    
    def check_args(self, args):
        #Setup logging
        if args.log_config:
            logging.config.fileConfig(args.log_config)
            self.log = logging.getLogger('pselastic')
        else:
            logging.basicConfig(format="time=%(asctime)s level=%(levelname)s %(message)s")
            self.log = logging.getLogger() 
            if args.verbose:
                self.log.setLevel(logging.DEBUG)
            else:
                self.log.setLevel(logging.INFO)
            
        #basic arg checking
        if args.action is None or len(args.action)==0:
            self.log.error("msg=You must specify an action. Valid values are: {0}".format(self.valid_actions))
            sys.exit(1)
        if args.action[0] not in self.valid_actions:
            self.log.error("msg=Action {0} is invalid. Valid values are: {1}".format(args.action[0], self.valid_actions))
            sys.exit(1)
        
        #check for URL environment variable
        if not args.elastic_url:
            args.elastic_url = os.environ.get('PSELASTIC_URL', DEFAULT_ELASTIC_URL)
        
        #check for login file environment variable
        if not args.elastic_login_file:
            args.elastic_login_file = os.environ.get('PSELASTIC_LOGIN_FILE', None)
            
        #Check if we are doing auth 
        self.auth = None
        if args.elastic_login_file:
            user_pass = ""
            with open(args.elastic_login_file) as login_file:
                user_pass = login_file.readline().rstrip()
            creds = user_pass.split(' ', 1)
            if creds:
                self.auth = HTTPBasicAuth(creds[0], creds[1])
            else:
                self.log.error("Unable to parse {0}. Needs to be one line with username and password separated by single space.".format(args.elastic_login_file))
                sys.exit(1)
        elif os.environ.get('PSELASTIC_USER', None) and os.environ.get('PSELASTIC_PASS', None):
            self.auth = HTTPBasicAuth(os.environ.get('PSELASTIC_USER'), os.environ.get('PSELASTIC_PASS'))
        
        #make these available if we don't want to do everything
        self.subactions=args.subactions
    
    def test_elastic(self, args):
        #0. Wait for elastic to come up
        retries = 0
        connected=False
        while retries <= args.max_retries and not connected:
            retries += 1
            r=None
            try:
                r = requests.get(url=args.elastic_url, auth=self.auth)
                r.raise_for_status()
                connected=True
            except:
                if r is not None:
                    self.log.error(r.text)
                retry_str=" Last attempt."
                if retries <= args.max_retries:
                    retry_str = " Will retry again in {0} second(s).".format(args.retry_wait)
                self.log.error("msg=Unable to connect to elastic.{0}".format(retry_str))
                time.sleep(args.retry_wait)
        
        return connected

    def run(self):
        parser= self.build_arg_parser()
        args = parser.parse_args()
        self.check_args(args)
        
        #Get down to business
        if args.periodic > 0:
            self.log.info("resources={0} action={1} msg=Started".format(self.resource, args.action[0]))
        while True:
            connected = self.test_elastic(args)
            if connected:
                self.handle_command(args)
            else:
                self.log.error("msg=Unable to connect to elasticsearch after {0} attempts.".format(args.max_retries+1))
            
            # if periodic, sleep, otherwise we are done
            if args.periodic > 0:
                time.sleep(args.periodic)
            else:
                break
