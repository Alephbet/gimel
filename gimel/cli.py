import click
import logging
try:
    from gimel import logger
    from gimel.deploy import run, js_code_snippet, preflight_checks, dashboard_url
    from gimel.config import config, config_filename, generate_config
except ImportError:
    import logger
    from deploy import run, js_code_snippet, preflight_checks, dashboard_url
    from config import config, config_filename, generate_config

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
    if not config:
        logger.info('generating new config {}'.format(config_filename))
        generate_config(config_filename)
    click.edit(filename=config_filename)


@cli.command()
@click.option('--namespace', default='alephbet')
def dashboard(namespace):
    click.launch(dashboard_url(namespace))


if __name__ == '__main__':
    cli()
