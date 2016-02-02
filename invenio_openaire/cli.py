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

import click
from flask_cli import with_appcontext


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
    from invenio_openaire.tasks import harvest_fundref
    harvest_fundref.delay(path=source)
    click.echo("Background task sent to queue.")


@openaire.command()
@click.option(
    '--source',
    type=click.Path(file_okay=True, dir_okay=False, readable=True,
                    resolve_path=True, exists=True),
    help="Local OpenAIRE SQLite database.",)
@with_appcontext
def loadgrants(source=None):
    """Harvest funders from FundRef."""
    from invenio_openaire.tasks import harvest_openaire_projects
    harvest_openaire_projects.delay(path=source)
    click.echo("Background task sent to queue.")
