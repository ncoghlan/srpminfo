# SRPM metadata extractor

This is a simple SRPM metadata extraction and caching server that stores
URL-keyed SRPM details in memory.

## Deployment Notes

This is a simple Flask app that runs under gunicorn in OpenShift v3. It relies
on `rpmdevtools` for the actual SRPM processing.

It currently does the SRPM processing synchronously in the request handling
thread, so don't expect this to scale well to multiple users - it's intended
for a *single* user to avoid repeatedly parsing the same SRPMs by using
a personal OpenShift v3 service to handle the actual metadata extraction.

Rearchitecting it to handle multiple users and persistent results storage will
likely make sense eventually, that's just more complex than I personally need
right now :)

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
