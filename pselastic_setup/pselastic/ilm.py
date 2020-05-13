#!/usr/bin/env python3

from utils import *

class PSElasticILMUtil(PSElasticUtil):
    
    def __init__(self):
        self.resource = 'ilm'
        self.valid_actions = [ "install" ]

    def handle_command(self, args):
        action = args.action[0]
        if action == "install":
            self.load_from_file(
                action, 
                url_path_prefix="_ilm/policy", 
                config_dir=args.config_dir, 
                elastic_url=args.elastic_url
            )
        else:
            log.error("Unknown action {0}".format(action))
            sys.exit(1)

'''
Handle when called from command-line
'''
if __name__ == "__main__":
    PSElasticILMUtil().run()