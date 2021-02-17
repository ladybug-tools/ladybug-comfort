"""ladybug-comfort commands."""
import click

from ladybug.cli import main
from .epw import epw
from .sql import sql
from .map import map


# command group for all comfort extension commands.
@click.group(help='ladybug comfort commands.')
@click.version_option()
def comfort():
    pass


# add sub-groups for comfort
comfort.add_command(epw)
comfort.add_command(sql)
comfort.add_command(map)


# add comfort sub-group to ladybug CLI
main.add_command(comfort)
