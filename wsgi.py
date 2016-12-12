"""SRPM metadata caching service"""
import logging
from functools import singledispatch

import attr
from flask import Flask, jsonify, request
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
    def get(self):
        remote_url = request.args['remote_url']
        return jsonify(srpminfo.lookup_source(remote_url))

class SRPM(Resource):
    def get(self):
        remote_url = request.args['remote_url']
        return jsonify(srpminfo.lookup_srpm(remote_url))

ENDPOINTS = (
    ("srpms", SRPM, '/srpms/'),
    ("sources", Source, '/sources/'),
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
    logger = logging.getLogger('srpminfo')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

def _setup_cache_backend():
    import os
    redis_host = os.environ.get("REDIS_HOST", "redis")
    srpminfo.configure_cache(redis_host)

# Run setup outside the __main__ guard so it also runs under a WSGI
# server which imports this as a module, rather than it being run as
# the main script.
_setup_logging()
_setup_cache_backend()

if __name__ == "__main__":
    application.run()
