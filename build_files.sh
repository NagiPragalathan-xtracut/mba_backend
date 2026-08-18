#!/usr/bin/env bash
# Vercel build step.
#
# The Python function bundle is built separately by @vercel/python; this script
# only produces the static assets the CDN serves. `collectstatic` needs Django
# importable, so the requirements are installed first.
#
# `DJANGO_ENV=vercel` is set in vercel.json, which means the settings module
# demands USE_S3 and the AWS_* variables - they must exist in the Vercel
# project's environment for the build to succeed, not just at runtime.
set -euo pipefail

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

python3 manage.py collectstatic --noinput --clear
