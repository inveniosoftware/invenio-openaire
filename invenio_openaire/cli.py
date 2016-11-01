# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""CLI for OpenAIRE module."""

from __future__ import absolute_import, print_function

import os

import click
from flask.cli import with_appcontext

from invenio_openaire.loaders import OAIREDumper
from invenio_openaire.tasks import harvest_fundref, harvest_openaire_projects


@click.group()
def openaire():
    """Command for loading OpenAIRE data."""


@openaire.command()
@click.option(
    '--source',
    type=click.Path(file_okay=True, dir_okay=False, readable=True,
                    resolve_path=True, exists=True),
    help="FundRef RDF registry data file.")
@with_appcontext
def loadfunders(source=None):
    """Harvest funders from FundRef."""
    harvest_fundref.delay(source=source)
    click.echo("Background task sent to queue.")


@openaire.command()
@click.option(
    '--source',
    type=click.Path(file_okay=True, dir_okay=False, readable=True,
                    resolve_path=True, exists=True),
    help="Local OpenAIRE SQLite database.")
@click.option(
    '--setspec', '-s',
    type=str,
    default='projects',
    help="Set to harvest (default: projects).")
@with_appcontext
def loadgrants(source=None, setspec=None):
    """Harvest grants from OpenAIRE."""
    harvest_openaire_projects.delay(source=source, setspec=setspec)
    click.echo("Background task sent to queue.")


@openaire.command()
@click.argument(
    'destination',
    type=click.Path(file_okay=True, dir_okay=False,
                    readable=True, resolve_path=True))
@click.option(
    '--as_json',
    type=bool,
    default=True,
    help="Convert XML to JSON before saving? (default: True)")
@click.option(
    '--setspec', '-s',
    type=str,
    help="Set to harvest and dump (default: projects).")
@with_appcontext
def dumpgrants(destination, as_json=None, setspec=None):
    """Harvest grants from OpenAIRE and store them locally."""
    if os.path.isfile(destination):
        click.confirm("Database '{0}' already exists."
                      "Do you want to write to it?".format(destination),
                      abort=True)  # no cover
    dumper = OAIREDumper(destination,
                         setspec=setspec)
    dumper.dump(as_json=as_json)
