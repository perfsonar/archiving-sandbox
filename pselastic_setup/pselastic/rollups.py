#!/usr/bin/env python3

from utils import *
import requests

class PSElasticRollupUtil(PSElasticUtil):
    
    def __init__(self):
        self.resource = 'rollups'
        self.valid_actions = [ "install", "cleanup" ]
        self.rollups_exist = {}

    '''
    Check if the index being rolled-up exists since rollup job can't be created until it does
    '''
    def need_rollup(self, job_name, job, elastic_url):
        self.log.debug("resource=rollups action=need_rollup.start")
        
        #1. First check if rollup job exists in cache
        if job_name in self.rollups_exist:
            self.log.debug("resource=rollups action=need_rollup.end msg=Rollup exists in cache")
            return False

        #2. Next check if exists in Elastic
        url = "{0}/_rollup/job/{1}".format(elastic_url, job_name)
        try:
            self.log.debug("resource=rollups action=check_rollup.start url={0}".format(url))
            r = requests.get(url=url, auth=self.auth)
            r.raise_for_status()
            #if have jobs, then we do not need to create
            if r.json() and r.json().get("jobs", None):
                self.log.debug("resource=rollups action=check_rollup.end url={0} status={1} elastic_reponse={2}".format(url, r.status_code, r.text))
                self.log.debug("resource=rollups action=need_rollup.end msg=Rollup exists in elastic")
                self.rollups_exist[job_name] = True
                return False
            self.log.debug("resource=rollups action=check_rollup.end url={0} status={1} elastic_reponse={2}".format(url, r.status_code, r.text))
        except:
            self.log.error("resource=rollups action=check_rollup.error url={0} msg={1}".format(url, sys.exc_info()))

        #3. Next check if index to rollup exists which is required to create
        #Get index_pattern from rollup job definition
        index_pattern = job.get("index_pattern", None)
        if not index_pattern:
            self.log.error("resource=rollups action=need_rollup.error msg=Rollup job missing index_patterns")
            return False
        #build URL
        url = "{0}/{1}".format(elastic_url, index_pattern)
        #Get the index
        create_rollup = False
        try:
            self.log.debug("resource=rollups action=check_source_index.start url={0}".format(url))
            r = requests.get(url=url, auth=self.auth)
            r.raise_for_status()
            #if a non-empty json object, then we are good
            if r.json():
                create_rollup = True
            self.log.debug("resource=rollups action=check_source_index.end url={0} status={1} elastic_reponse={2}".format(url, r.status_code, r.text))
        except:
            self.log.error("resource=rollups action=check_source_index.error url={0} msg={1}".format(url, sys.exc_info()))
        
        self.log.debug("resource=rollups action=need_rollup.end")
        return create_rollup

    '''
    Start a rollub job using the Elastic REST API
    '''
    def start_rollup_job(self, job_name, job, elastic_url):
        url = "{0}/_rollup/job/{1}/_start".format(elastic_url, job_name)
        try:
            self.log.debug("resource=rollups action=start_job.start url={0}".format(url))
            r = requests.post(url=url, auth=self.auth)
            r.raise_for_status()
            self.log.debug("resource=rollups action=start_job.end url={0} status={1} elastic_reponse={2}".format(url, r.status_code, r.text))
        except:
            self.log.error("resource=rollups action=start_job.error url={0} msg={1}".format(url, sys.exc_info()))

    def handle_command(self, args):
        action = args.action[0]
        if action == "install":
            self.load_from_file(
                action, 
                url_path_prefix="_rollup/job",
                config_dir=args.config_dir,
                elastic_url=args.elastic_url,
                pre_func=self.need_rollup, 
                post_func=self.start_rollup_job
            )
        elif action == "cleanup":
            self.load_from_file(
                action, 
                url_path_suffix="_delete_by_query",
                config_dir=args.config_dir,
                elastic_url=args.elastic_url,
                http_method=requests.post
            )
        else:
            log.error("Unknown action {0}".format(action))
            sys.exit(1)

'''
Handle when called from command-line
'''
if __name__ == "__main__":
    PSElasticRollupUtil().run()