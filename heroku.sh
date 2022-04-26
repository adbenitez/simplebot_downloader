#!/bin/bash

# configure the bot
python3 -m simplebot init "$ADDR" "$PASSWORD"
python3 -m simplebot -a "$ADDR" set_name "File Downloader"
python3 -m simplebot -a "$ADDR" set_config e2ee_enabled 0  # disable encryption to avoid issues with key lost

# add the youtube plugin
python3 -m pip install youtube-dl # required by youtube.py plugin
python3 -c "import requests; r=requests.get('https://github.com/adbenitez/simplebot-scripts/raw/master/scripts/youtube.py'); open('youtube.py', 'wb').write(r.content)"
python3 -m simplebot -a "$ADDR" plugin --add ./youtube.py

# add admin plugin
if [ -n "$ADMIN" ]; then
    python3 -m pip install psutil # required by admin.py plugin
    python3 -c "import requests; r=requests.get('https://github.com/adbenitez/simplebot-scripts/raw/master/scripts/admin.py'); open('admin.py', 'wb').write(r.content)"
    python3 -m simplebot -a "$ADDR" plugin --add ./admin.py
    python3 -m simplebot -a "$ADDR" admin --add "$ADMIN"
fi

# start the bot
python3 -m simplebot -a "$ADDR" serve
