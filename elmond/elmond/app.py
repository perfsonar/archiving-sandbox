import logging
from json import dumps
from elasticsearch import Elasticsearch
from flask import Flask, Response, request
from metadata import EsmondMetadata
from werkzeug.exceptions import NotFound

app = Flask(__name__)

#todo: error handling
#todo: make connection option configurable
es = Elasticsearch(['elasticsearch'])

#function for dumping a json response
def json_response(obj):
    text = dumps(obj,
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
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
