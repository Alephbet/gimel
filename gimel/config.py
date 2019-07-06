from __future__ import print_function
from os.path import expanduser, realpath
import os
import json
try:
    from gimel import logger
except ImportError:
    import logger

logger = logger.setup()


# NOTE: Copy config.json.template to config.json and edit with your settings

def _load_config(config_filename):
    try:
        with open(config_filename) as config_file:
            logger.info('Using config {}'.format(config_filename))
            return config_file.name, json.load(config_file)
    except IOError:
        logger.debug('trying to load {} (not found)'.format(config_filename))
        return config_filename, {}


def load_config():
    config_filenames = (realpath('config.json'),
                        expanduser('~/.gimel/config.json'))
    for config_filename in config_filenames:
        name, content = _load_config(config_filename)
        if content:
            break
    return name, content


def _create_file(config_filename):
    dirname = os.path.split(config_filename)[0]
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    with os.fdopen(os.open(config_filename,
                           os.O_WRONLY | os.O_CREAT, 0o600), 'w'):
        pass


def _config_template():
    from pkg_resources import resource_filename as resource
    return open(resource('gimel', 'config.json.template'), 'r').read()


def generate_config(config_filename=None):
    if config_filename is None:
        config_filename = expanduser('~/.gimel/config.json')
    _create_file(config_filename)

    with open(config_filename, 'w') as config_file:
        config_file.write(_config_template())
    return config_filename


config_filename, config = load_config()
