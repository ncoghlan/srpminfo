"""SRPM metadata caching service"""
import logging
from functools import singledispatch

import attr
from flask import Flask, jsonify
from flask_restful import Resource, Api

import srpminfo

##############################################
# Set up the REST API
##############################################
log = logging.getLogger(__name__)

class ThisAPI(Api):
    def handle_error(self, exc):
        # Delegate error handling to the module level handler below
        log.error(str(exc))
        return handle_api_error(exc)

application = Flask(__name__)
the_api = ThisAPI(application)

##############################################
# Error handling
##############################################
@singledispatch
def handle_api_error(exc):
    # Default to Flask-RESTFul's standard error handling
    return super(ThisAPI, the_api).handle_error(exc)

@handle_api_error.register(srpminfo.RemoteLookupError)
def _handle_remote_lookup_error(exc):
    details = dict(
        error='Unable to access given remote URL',
        error_details=attr.asdict(exc),
    )
    return jsonify(details), 404

@handle_api_error.register(srpminfo.InvalidSRPM)
def _handle_invalid_srpm(exc):
    details = dict(
        error='Unable to parse referenced SRPM',
        error_details=attr.asdict(exc),
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
def _setup_logging():
    # create logger with 'spam_application'
    logger = logging.getLogger('srpminfo')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

if __name__ == "__main__":
    _setup_logging()
    srpminfo.configure_cache("~/srpminfo/cachefile.dbm")
    application.run()
