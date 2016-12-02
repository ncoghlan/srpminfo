"""Helper module to cache SRPM metadata"""
import tempfile

from attr import attributes, attrib
import requests
import sarge

# Just using in memory data storage for now
@attributes
class UpstreamSource:
    url = attrib()
    sha256 = attrib()

@attributes
class CachedSRPM:
    epoch = attrib()
    name = attrib()
    version = attrib()
    release = attrib()
    sources = attrib()

# Escaped URL keyed dicts for source artifacts and SRPMs
source_db = {}
srpm_db = {}

# Error results
@attributes(str=True)
class RemoteLookupError(Exception):
    """Failed to look up given remote URL"""
    remote_url = attrib()

@attributes(str=True)
class InvalidSRPM(Exception):
    """Processing of given SRPM failed"""
    remote_url = attrib()

# Query endpoints
def lookup_source(remote_url):
    """Report hash details for a given URL (retrieving and hashing as needed)"""
    raise RemoteLookupError(remote_url)

def lookup_srpm(remote_url):
    """Report SRPM details for a given URL (retrieving and parsing as needed)"""
    raise InvalidSRPM(remote_url)
