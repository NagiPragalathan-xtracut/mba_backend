#!/usr/bin/env bash
# Vercel build step.
#
# The Python function bundle is built separately by @vercel/python; this script
# only produces the static assets the CDN serves. `collectstatic` imports the
# settings module, so the full requirements must be installed first.
#
# `DJANGO_ENV=vercel` is set in vercel.json, which means the settings module
# demands USE_S3 and the AWS_* variables - they must exist in the Vercel
# project's environment for the build to succeed, not just at runtime.
set -euo pipefail

# PEP 668: the build image's system Python is marked "externally managed", so
# pip refuses to install into it and exits with `externally-managed-environment`.
# A virtualenv is the clean way around that. If the image cannot create one,
# fall back to overriding the marker via the environment variable (pip reads it
# for every command, unlike the --break-system-packages flag which is valid only
# on `install`). The build container is disposable, so there is no system
# installation worth protecting.
PYTHON=python3
if python3 -m venv .venv 2>/dev/null; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
    PYTHON=python
else
    export PIP_BREAK_SYSTEM_PACKAGES=1
fi

$PYTHON -m pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

$PYTHON manage.py collectstatic --noinput --clear
