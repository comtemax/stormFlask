#!/bin/bash

. venv/bin/activate

export FLASK_ENV=development

python3 -m flask run --port 8085
