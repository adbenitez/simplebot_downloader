#!/bin/bash

# configure the bot
python3 -m simplebot init "$ADDR" "$PASSWORD"
python3 -m simplebot -a "$ADDR" set_name "File Downloader"

# add the youtube plugin
python3 -m pip install youtube-dl # required by youtube.py plugin
python3 -c "import requests; r=requests.get('https://github.com/adbenitez/simplebot-scripts/raw/master/scripts/youtube.py'); open('youtube.py', 'wb').write(r.content)"
python3 -m simplebot -a "$ADDR" plugin --add ./youtube.py

# add the encryption_error plugin to leverage key changes
python3 -c "import requests; r=requests.get('https://github.com/adbenitez/simplebot-scripts/raw/master/scripts/encryption_error.py'); open('encryption_error.py', 'wb').write(r.content)"
python3 -m simplebot -a "$ADDR" plugin --add ./encryption_error.py

# add admin plugin
if [ -n "$ADMIN" ]; then
    python3 -m pip install psutil # required by admin.py plugin
    python3 -c "import requests; r=requests.get('https://github.com/adbenitez/simplebot-scripts/raw/master/scripts/admin.py'); open('admin.py', 'wb').write(r.content)"
    python3 -m simplebot -a "$ADDR" plugin --add ./admin.py
    python3 -m simplebot -a "$ADDR" admin --add "$ADMIN"
fi

# start the bot
python3 -m simplebot -a "$ADDR" serve
