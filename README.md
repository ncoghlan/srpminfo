# SRPM metadata extractor

This is a simple SRPM metadata extraction and caching server that caches
URL-keyed SRPM details in Redis.

## API Usage

The API server exposes two useful endpoints:

    <API_BASE>/sources/?remote_url=<remote_artifact_url>
    <API_BASE>/srpms/?remote_url=<remote_artifact_url>

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
directly from the Redis cache, rather than needing to be downloaded again.

## Deployment Notes

This is a basic Flask app that runs under gunicorn in OpenShift v3. It relies
on `rpmdevtools` for the actual SRPM processing.

By default, it assumes that the Redis backend will be accessible as `redis`
from the front-end containers, but this can be overridden by setting
`REDIS_HOST` in the environment.

The Redis caching is currently unbounded and there are no constraints on the
URLs accessed, so exposing this as an accessible endpoint on an untrusted
network would be a Bad Idea.

However, it's fine for its intended purpose, which is to allow individuals
or smallish teams to avoid repeatedly extracting the same metadata from a
common set of SRPMs.


## Deployment Steps

These deployment steps assume you've already logged in to the target
OpenShift v3 cluster with `oc login`.

The `rpmdevtools` dependency means this image requires a custom s2i builder:

```
$ cat Dockerfile | oc new-build --name python35-rpmdevtools-s2i --dockerfile -
```

That builder image must then be specified when first creating the app:

```
$ oc new-app python35-rpmdevtools-s2i~https://github.com/ncoghlan/srpminfo.git
$ oc expose svc srpminfo
```

To subsequently update the deployed app to the latest state of the repo:

```
$ oc start-build srpminfo
```

## Redis Deployment Steps

If `REDIS_HOST` isn't set explicitly to an externally hosted Redis instance,
the project must also include its own Redis instance to store the metadata
cache, and that may require a little fiddling as generally available images
require additional user permissions to run on OpenShift v3.2 and earlier.

First try using either the default `redis` image or the CentOS based one:

```
$ oc new-app redis
```

```
$ oc new-app centos/redis-32-centos7
```

If both the default Docker `redis` image and the `centos/redis-32-centos7`
image fail to start correctly on your cluster, try doing the following
instead to explicitly disable any attempts to persist the cached Redis data:

```
$ cat Dockerfile.redis | oc new-build --name redis-stateless --dockerfile -
$ oc new-app --name=redis --image-stream=redis-stateless --allow-missing-imagestream-tags
```

To clean these up in order to recreate them for some reason:

```
$ oc delete all -l app=redis
$ oc delete all -l build=redis-stateless
```
