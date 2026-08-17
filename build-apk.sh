#!/usr/bin/env bash
set -e
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install buildozer cython
buildozer android debug
