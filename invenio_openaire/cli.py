# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI for OpenAIRE module."""

from __future__ import absolute_import, print_function

import json
import os

import click
from flask.cli import with_appcontext

from invenio_openaire.loaders import LocalOAIRELoader, OAIREDumper, \
    LocalJSONOAIRELoader
from invenio_openaire.tasks import harvest_all_openaire_projects, \
    harvest_fundref, harvest_openaire_projects, register_grant


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
    '--format', '-f',
    type=str,
    default='json',
    help="Format of the source file to load.")
@click.option(
    '--setspec', '-s',
    type=str,
    default=None,
    help="Set to harvest.")
@click.option(
    '--all', '-A', 'all_grants',
    default=False,
    is_flag=True,
    help="Harvest all grants (default: False).")
@with_appcontext
def loadgrants(source=None, setspec=None, format=None, all_grants=False):
    """Harvest grants from OpenAIRE.

    :param source: Load the grants from a local sqlite db (offline).
        The value of the parameter should be a path to the local file.
    :type source: str
    :param setspec: Harvest specific set through OAI-PMH
        Creates a remote connection to OpenAIRE.
    :type setspec: str
    :param format: str
    :type format: Specify the grant dump's format.
    :param all_grants: Harvest all sets through OAI-PMH,
        as specified in the configuration OPENAIRE_GRANTS_SPEC. Sets are
        harvested sequentially in the order specified in the configuration.
        Creates a remote connection to OpenAIRE.
    :type all_grants: bool
    """
    assert all_grants or setspec or source, \
        "Either '--all', '--setspec' or '--source' is required parameter."
    if all_grants:
        harvest_all_openaire_projects.delay()
    elif setspec:
        click.echo("Remote grants loading sent to queue.")
        harvest_openaire_projects.delay(setspec=setspec)
    else:  # if source
        if format == 'json':
            click.echo("Loading grants from file.")
            click.echo(source)
            loader = LocalJSONOAIRELoader(source=source)
            for grant_json in loader.iter_grants():
                register_grant.si(grant_json).apply()
        else:
            loader = LocalOAIRELoader(source=source)
            loader._connect()
            cnt = loader._count()
            click.echo("Sending grants to queue.")
            with click.progressbar(loader.iter_grants(), length=cnt) as grants_bar:

                for grant_json in grants_bar:
                    register_grant.delay(grant_json)


@openaire.command()
@click.option(
    '--source',
    type=click.Path(file_okay=True, dir_okay=False, readable=True,
                    resolve_path=True, exists=True),
    help="JSON file with grant information.")
@with_appcontext
def registergrant(source=None, setspec=None):
    """Harvest grants from OpenAIRE."""
    with open(source, 'r') as fp:
        data = json.load(fp)
    register_grant(data)


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
