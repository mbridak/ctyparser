#!/bin/bash
pip uninstall -y notctyparser
rm dist/*
python3 -m build
pip install -e .

