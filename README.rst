.. image:: https://www.herokucdn.com/deploy/button.svg
   :target: https://heroku.com/deploy?template=https://github.com/adbenitez/simplebot_downloader/tree/master/


"Downloader" SimpleBot Plugin
=============================

.. image:: https://img.shields.io/pypi/v/simplebot_downloader.svg
   :target: https://pypi.org/project/simplebot_downloader

.. image:: https://img.shields.io/pypi/pyversions/simplebot_downloader.svg
   :target: https://pypi.org/project/simplebot_downloader

.. image:: https://pepy.tech/badge/simplebot_downloader
   :target: https://pepy.tech/project/simplebot_downloader

.. image:: https://img.shields.io/pypi/l/simplebot_downloader.svg
   :target: https://pypi.org/project/simplebot_downloader

.. image:: https://github.com/adbenitez/simplebot_downloader/actions/workflows/python-ci.yml/badge.svg
   :target: https://github.com/adbenitez/simplebot_downloader/actions/workflows/python-ci.yml

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

A `SimpleBot`_ plugin that allows to download files by email/DeltaChat.

Install
-------

To install run::

  pip install simplebot-downloader

Customization
-------------

By default the maximum file size allowed is 150MB, to change it, pass the number of bytes as follows::

  simplebot -a bot@example.com db -s simplebot_downloader/max_size 10485760

By default the file will be sent in several emails split in chunks of 15728640 Bytes (15MB), to change it::

  simplebot -a bot@example.com db -s simplebot_downloader/part_size 10240

By default there is a delay of 60 seconds between each sent chunk, to change it::

  simplebot -a bot@example.com db -s simplebot_downloader/delay 120


.. _SimpleBot: https://github.com/simplebot-org/simplebot
