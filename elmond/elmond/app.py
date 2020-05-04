import logging
import logging.config
import json
import os
import sys
from elasticsearch import Elasticsearch
from flask import Flask, Response, request, g
from metadata import EsmondMetadata
from werkzeug.exceptions import NotFound

def create_app(test_config=None):
    app = Flask(__name__)
    
    #Identify config files using ELMOND_ROOT envionment variable
    config_dir = os.environ.get('ELMOND_ROOT', '/etc/elmond')
    config_filename = "{0}/elmond.json".format(config_dir)
    logging_config_filename = "{0}/logging.conf".format(config_dir)
    
    #load config file
    if test_config:
        config = test_config
        log = logging.getLogger()
        log.setLevel(logging.DEBUG)
        log.addHandler(logging.StreamHandler(sys.stdout))
        log.debug("Using test configurtation")
    else:
        #setup logging
        logging.config.fileConfig(logging_config_filename)
        log = logging.getLogger('elmond')
        log.debug("Welcome to elmond!")
        #load config
        with open(config_filename) as config_file:
            config = json.load(config_file)
        log.debug("Loaded configuration from {0}".format(config_filename))
    
    #set to application context so can use as needed
    app.config['ELMOND'] = config
    
    #todo: error handling
    es_hosts = config.get("ELASTIC_HOSTS", ['localhost'])
    elastic_params = config.get("ELASTIC_PARAMS", {})
    es = Elasticsearch(es_hosts, **elastic_params)

    #function for dumping a json response
    def json_response(obj):
        text = json.dumps(obj,
                     sort_keys=True,
                     indent=4,
                     separators=(',', ': ')
                    )
        return Response(text + '\n',
                        mimetype='application/json')
                
                
    @app.route('/', methods=['GET'])
    def list_metadata():
        emd = EsmondMetadata(es)
        metadata = emd.search(q=request.args, request_url=request.url, paginate=True)
        return json_response(metadata)

    @app.route('/<metadata_key>', methods=['GET'])
    def get_metadata(metadata_key):
        emd = EsmondMetadata(es)
        metadata = emd.search(q={'metadata-key': metadata_key}, request_url=request.url)
        if len(metadata) == 0:
            raise NotFound("Unable to find metadata with key {0}".format(metadata_key))
            
        return json_response(metadata[0])
    
    return app
    
if __name__ == '__main__':
    create_app().run(debug=True, host='0.0.0.0')
