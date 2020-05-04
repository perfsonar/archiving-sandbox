import logging
from json import dumps
from elasticsearch import Elasticsearch
from flask import Flask, Response, request
from metadata import EsmondMetadata

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
def get_metadata():
    emd = EsmondMetadata(es)
    metadata = emd.search(q=request.args, request_url=request.url)
    return json_response(metadata)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
