#!/bin/bash
alias bot='python3 -m simplebot -a "$ADDR"'

# install deps
python3 -m pip install git+https://github.com/adbenitez/simplebot_downloader
python3 -m pip install psutil # required by admin.py plugin
python3 -m pip install youtube-dl # required by youtube.py plugin

# download extra plugins
python3 -c "import requests; r=requests.get('https://github.com/adbenitez/simplebot-scripts/raw/master/scripts/youtube.py'); open('youtube.py', 'wb').write(r.content)"
python3 -c "import requests; r=requests.get('https://github.com/adbenitez/simplebot-scripts/raw/master/scripts/admin.py'); open('admin.py', 'wb').write(r.content)"

# configure the bot
python3 -m simplebot init "$ADDR" "$PASSWORD"
bot set_config e2ee_enabled 0  # disable encryption to avoid issues with key lost
bot plugin --add ./admin.py
bot plugin --add ./youtube.py
if [ -z "$ADMIN" ]; then
    bot admin --add "$ADMIN"
fi

# start the bot
bot serve
