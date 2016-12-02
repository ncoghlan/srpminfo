"""Helper module to cache SRPM metadata"""
import logging
import pathlib
import tempfile
from contextlib import contextmanager
from itertools import starmap
from os.path import basename

from attr import attributes, attrib, asdict
from dogpile.cache import make_region
import requests
import sarge

log = logging.getLogger(__name__)

##############################################
# Response caching
##############################################
# Just using in memory data storage for now
cache_region = make_region().configure(
    'dogpile.cache.memory'
)

##############################################
# Query APIs
##############################################
@attributes
class UpstreamSource:
    url = attrib()
    sha256 = attrib()

@attributes
class CachedSRPM:
    name = attrib()
    epoch = attrib()
    version = attrib()
    release = attrib()
    sources = attrib()

@cache_region.cache_on_arguments()
def lookup_source(remote_url):
    """Report hash details for a given URL (retrieving and hashing as needed)"""
    with _tempdir() as tmpdir:
        source_path = _download_file(remote_url, tmpdir)
        source_hash = _compute_sha256_digest(source_path)
    return asdict(UpstreamSource(remote_url, source_hash))

@cache_region.cache_on_arguments()
def lookup_srpm(remote_url):
    """Report SRPM details for a given URL (retrieving and parsing as needed)"""
    with _tempdir() as tmpdir:
        srpm_path = _download_file(remote_url, tmpdir)
        try:
            metadata = _read_srpm_metadata(srpm_path)
            contents = _extract_srpm_contents(srpm_path, tmpdir)
            spec, source_urls, source_paths = _get_source_paths(tmpdir)
            source_hashes = map(_compute_sha256_digest, source_paths)
            sources = [asdict(UpstreamSource(url, hash))
                           for url, hash in zip(source_urls, source_hashes)]
        except Exception as exc:
            raise InvalidSRPM(remote_url, str(exc)) from exc
    return asdict(CachedSRPM(sources=sources, **metadata))


##############################################
# Error results
##############################################
@attributes(str=True)
class RemoteLookupError(Exception):
    """Failed to look up given remote URL"""
    remote_url = attrib()
    status_code = attrib()
    reason = attrib()
    raw_response = attrib()

@attributes(str=True)
class InvalidSRPM(Exception):
    """Processing of given SRPM failed"""
    remote_url = attrib()
    error = attrib()


##############################################
# Miscellaneous utilities
##############################################
@contextmanager
def _tempdir():
    """pathlib.Path based temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield pathlib.Path(tmpdir)

def _download_file(url, target_dir, *, local_filename=None, auth=None):
    """Download file from given URL into `target_dir`"""
    log.debug("Fetching artifact from: %s", url)
    local_filename = local_filename or url.split('/')[-1]
    local_path = target_dir / local_filename

    try:
        r = requests.get(url, auth=auth, stream=True)
    except Exception as exc:
        raise RemoteLookupError(url, None, None, str(exc)) from exc
    if r.status_code != 200:
        raise RemoteLookupError(r.url, r.status_code, r.reason, r.raw)

    log.debug("Downloading artifact to %s", local_path)
    with local_path.open('wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    return local_path

def _read_srpm_metadata(srpm_path):
    """Read SRPM metadata using the `rpm` utility"""
    command = ['rpm','--query','--package','--info', str(srpm_path)]
    log.debug("Reading SRPM metadata: %r", command)
    rpm_output = sarge.get_stdout(command)
    keys_of_interest = "Epoch Name Version Release".split()
    metadata = dict.fromkeys(map(str.lower, keys_of_interest))
    for line in rpm_output.splitlines():
        key, sep, value = line.partition(":")
        key = key.strip().lower()
        if key in metadata:
            metadata[key] = value.strip()
    return metadata

def _extract_srpm_contents(srpm_path, target_dir):
    """Extract an SRPM package using rpm2cpio / cpio into `target_dir`"""
    old_paths = set(target_dir.iterdir())
    raw_command = 'rpm2cpio {} | cpio -idm > /dev/null 2>&1'
    command = sarge.shell_format(raw_command, srpm_path)
    log.debug("Extracting SRPM contents: %r", command)
    sarge.run(command, cwd=str(target_dir))
    new_paths = sorted(set(target_dir.iterdir()) - old_paths)
    log.debug("Extracted files: %s", new_paths)
    return new_paths

def _get_source_paths(srpm_dir):
    """Gets the Specfile and all referenced SourceX files from `srpm_dir`"""
    specs = list(srpm_dir.glob("*.spec"))
    if len(specs) != 1:  # sanity
        msg = "Expected exactly 1 specfile in {path}, found {num}"
        raise RuntimeError(msg.format(num=len(specs), path=srpm_dir))

    # Source entry format:
    # Source0: http://pypi.python.org/packages/source/r/requests/requests-2.7.0.tar.gz
    #
    spec = specs.pop()
    source_urls = []
    paths = []
    log.debug("Querying specfile for sources: %s", spec)
    spectool_result = sarge.get_stdout(['spectool', '-S', str(spec)])
    for src in spectool_result.splitlines():
        name, url = src.split(" ", 1)
        source_urls.append(url)
        local_filename = basename(url)
        paths.append(srpm_dir / local_filename)
    log.debug("Local source paths: %s", paths)
    return spec, source_urls, paths

def _compute_sha256_digest(path):
    """Compute SHA256 digest of given path"""
    # Uses sha256sum, which returns e.g.:
    # 65ecde5d025fcf57ceaa32230e2ff884ab204065b86e0e34e609313c7bdc7b47  /etc/passwd
    input_path = str(path)
    data = sarge.get_stdout(["sha256sum", input_path])
    digest, sep, result_path = data.partition(' ')
    if not sep or result_path.strip() != input_path:
        log.error(data)
        raise RuntimeError("can't compute digest of %s" % path)
    log.debug("%s -> sha256: %s", path, digest)
    return digest
