#!/bin/bash
alias bot='python3 -m simplebot -a "$ADDR"'

# configure the bot
python3 -m simplebot init "$ADDR" "$PASSWORD"
bot set_config e2ee_enabled 0  # disable encryption to avoid issues with key lost

# add the youtube plugin
python3 -m pip install youtube-dl # required by youtube.py plugin
python3 -c "import requests; r=requests.get('https://github.com/adbenitez/simplebot-scripts/raw/master/scripts/youtube.py'); open('youtube.py', 'wb').write(r.content)"
bot plugin --add ./youtube.py

# add admin plugin
if [ -z "$ADMIN" ]; then
    python3 -m pip install psutil # required by admin.py plugin
    python3 -c "import requests; r=requests.get('https://github.com/adbenitez/simplebot-scripts/raw/master/scripts/admin.py'); open('admin.py', 'wb').write(r.content)"
    bot plugin --add ./admin.py
    bot admin --add "$ADMIN"
fi

# start the bot
bot serve
