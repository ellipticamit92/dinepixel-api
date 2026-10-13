#!/usr/bin/env bash
set -e

# Install poppler for PDF support (pdftoppm)
apt-get install -y poppler-utils

pip install -r requirements.txt
