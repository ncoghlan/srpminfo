# SRPM metadata extractor

This is a simple SRPM metadata extraction and caching server that caches
URL-keyed SRPM details in RAM.

## API Usage

The API server exposes two useful endpoints:

    <API_BASE>/sources/<remote_artifact_url>
    <API_BASE>/srpms/<remote_artifact_url>

The sources endpoint downloads the given remote artifact, hashes it
with `sha256sum`, and reports the result as:

    {
        "url": <remote_artifact_url>,
        "sha256": <remote_artifact_hash>
    }

The SRPMs endpoint downloads the given remote artifact, processes it with
`rpmdevtools` and reports the result as:

    {
        "name": <srpm_epoch>,
        "epoch": <srpm_epoch>,
        "version": <srpm_epoch>,
        "release": <srpm_epoch>,
        "sources": [
            {
                "url": <Source0_artifact_url>,
                "sha256": <Source0_artifact_hash>
            },
            {
                "url": <Source1_artifact_url>,
                "sha256": <Source1_artifact_hash>
            }
        ]
    }

Note that the hashes in the SRPM response are for the source artificats
*as stored in the SRPM*, allowing them to be checked against the hashes
obtained via the sources collection.

For both endpoints, future requests for the same remote URL will be answered
directly from the in-memory cache, rather than needing to be downloaded again.

## Deployment Notes

This is a simple Flask app that runs under gunicorn in OpenShift v3. It relies
on `rpmdevtools` for the actual SRPM processing.

It currently does the SRPM processing synchronously in the request handling
thread, so don't expect this to scale well to multiple users - it's intended
for a *single* user to avoid repeatedly parsing the same SRPMs by using
a personal OpenShift v3 service to handle the actual metadata extraction.

Rearchitecting it to better handle multiple users and to use Redis for storage
will likely make sense eventually, it's just more complex than I personally
need right now :)

## Deployment Steps

The `rpmdevtools` dependency means this image requires a custom s2i builder:

```
$ cat Dockerfile | oc new-build --name python35-rpmdevtools-s2i --dockerfile -
```

That builder must then be specified when creating the app:

```
oc new-app python35-rpmdevtools-s2i~https://github.com/ncoghlan/srpminfo.git
oc expose svc srpminfo
```
