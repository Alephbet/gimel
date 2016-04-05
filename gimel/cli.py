import click
import logging
import logger
from deploy import run, js_code_snippet, preflight_checks

logger = logger.setup()


@click.group()
@click.option('--debug', is_flag=True)
def cli(debug):
    if debug:
        logger.setLevel(logging.DEBUG)


@cli.command()
def preflight():
    logger.info('running preflight checks')
    preflight_checks()


@cli.command()
@click.option('--preflight/--no-preflight', default=True)
def deploy(preflight):
    if preflight:
        logger.info('running preflight checks')
        if not preflight_checks():
            return
    logger.info('deploying')
    run()
    js_code_snippet()


@cli.command()
def configure():
    from config import config, config_filename, generate_config
    if not config:
        logger.info('generating new config {}'.format(config_filename))
        generate_config(config_filename)
    click.edit(filename=config_filename)

if __name__ == '__main__':
    cli()
