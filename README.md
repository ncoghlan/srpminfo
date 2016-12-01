# SRPM metadata extractor

This is a simple SRPM metadata extraction and caching server that stores
URL-keyed SRPM details in memory (it may eventually store them in Redis
or a database).

## Deployment Notes

This is a simple Flask app that runs under gunicorn in OpenShift v3. It relies
on `rpmdevtools` for the actual SRPM processing.

## Deployment Steps

The `rpmdevtools` dependency means this image requires a customer s2i builder:

```
$ cat Dockerfile | oc new-build --name python35-rpmdevtools-s2i --dockerfile -
```

That builder must then be specified when creating the app:

```
oc new-app python35-rpmdevtools-s2i~https://github.com/ncoghlan/srpminfo.git
oc expose svc srpminfo
```
