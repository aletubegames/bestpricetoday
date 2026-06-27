#!/bin/bash
cp /home/alessandro/bin/Git_Repo/BestPriceToday/backend/bestprice_bot.service /etc/systemd/system/bestprice_bot.service
systemctl daemon-reload
systemctl enable bestprice_bot
systemctl start bestprice_bot
systemctl is-active bestprice_bot
