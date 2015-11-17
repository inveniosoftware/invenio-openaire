# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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

"""OpenAIRE service integration for Invenio repositories."""

from __future__ import absolute_import, print_function

from celery import shared_task
from flask import current_app
from sickle import Sickle


@shared_task(ignore_result=True)
def harvest_openaire_projects(from_=None):
    """Harvest grants from OpenAIRE and store as authority records."""
    # OAI-PMH harvester client
    client = Sickle(current_app.config['OPENAIRE_OAIPMH_ENDPOINT'])

    client.ListRecords(metadataPrefix='oaf', set='projects')

    # for record in records:
    #    create_authority_record.delay(record)


@shared_task(ignore_result=True)
def harvest_fundref():
    """Harvest funders from FundRef and store as authority records."""
    # Download fundref file and import data.


@shared_task(ignore_result=True)
def create_authority_record(identifier, record):
    """Create authority record for a harvested OAI-PMH record."""
