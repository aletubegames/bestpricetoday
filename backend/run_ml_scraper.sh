#!/bin/bash
cd /home/alessandro/backend
source venv/bin/activate
xvfb-run --auto-servernum --server-args='-screen 0 1920x1080x24' python -m app.workers.ml_scraper >> ml_scraper.log 2>&1
