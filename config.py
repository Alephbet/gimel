from __future__ import print_function
import json


# NOTE: Copy config.json.template to config.json and edit with your settings
def _load_config():
    try:
        with open('config.json') as config_file:
            return json.load(config_file)
    except IOError:
        print('Please check your config.json file!')
        return {}

config = _load_config()
