"""SRPM metadata caching service"""
from functools import singledispatch

from flask import Flask, jsonify
from flask_restful import Resource, Api, abort

import srpminfo

##############################################
# Set up the REST API
##############################################
class ThisAPI(Api):
    def handle_error(self, exc):
        # Delegate error handling to the module level handler below
        return _handle_error(exc)

application = Flask(__name__)
the_api = ThisAPI(application)

##############################################
# Error handling
##############################################
@singledispatch
def _handle_error(exc):
    # Default to Flask-RESTFul's standard error handling
    return super(ThisAPI, the_api).handle_error(exc)

@_handle_error.register(srpminfo.RemoteLookupError)
def _handle_remote_lookup_error(exc):
    details = dict(
        error='Unable to access given remote URL',
        remote_url=exc.remote_url,
    )
    return jsonify(details), 404

@_handle_error.register(srpminfo.InvalidSRPM)
def _handle_remote_lookup_failure(exc):
    details = dict(
        error='Unable to parse referenced SRPM',
        remote_url=exc.remote_url,
    )
    return jsonify(details), 400

##############################################
# Set up the API endpoints
##############################################
class Source(Resource):
    def get(self, remote_url):
        return jsonify(srpminfo.lookup_source(remote_url))

class SRPM(Resource):
    def get(self, remote_url):
        return jsonify(srpminfo.lookup_srpm(remote_url))

ENDPOINTS = (
    ("srpms", SRPM, '/srpms/<path:remote_url>'),
    ("sources", Source, '/sources/<path:remote_url>'),
)

RESOURCE_MAP = {}
for name, resource, path in ENDPOINTS:
    the_api.add_resource(resource, path)
    RESOURCE_MAP[name] = path

# And the base URL
@application.route("/")
def base_response():
    return jsonify(RESOURCE_MAP)

##############################################
# Launch the service
##############################################
if __name__ == "__main__":
    application.run()
