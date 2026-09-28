# Xvfb sidecar for PS-011. Small on purpose: Xvfb, xdpyinfo for the healthcheck, and
# ImageMagick's `import` for the screenshot check.
FROM debian:stable-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends xvfb x11-utils imagemagick \
    && rm -rf /var/lib/apt/lists/*
