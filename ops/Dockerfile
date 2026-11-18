# Garage ships as a scratch image containing only the static `/garage` binary,
# so the container has no shell — and the first run needs a few CLI steps
# (layout assign/apply, key import, bucket create) that cannot be expressed as
# S3 calls. This wrapper adds a busybox shell and keeps the daemon itself
# untouched: same binary, same version.
#
# The config and the start script are bind-mounted by docker-compose, so editing
# them does not require a rebuild.
FROM alpine:3.20

COPY --from=dxflrs/garage:v2.1.0 /garage /garage

ENTRYPOINT ["/bin/sh", "/garage-start.sh"]
