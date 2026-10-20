#!/bin/bash
cd /home/alessandro/backend
source venv/bin/activate
python -m app.workers.ml_coupon_scraper >> ml_coupon_scraper.log 2>&1
