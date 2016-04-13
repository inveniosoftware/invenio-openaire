# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
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

"""Resolve JSON for OpenAIRE grants."""

from __future__ import absolute_import, print_function

import jsonresolver
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record
from werkzeug.routing import Rule


def resolve_grant_endpoint(doi_grant_code):
    """Resolve the OpenAIRE grant."""
    # jsonresolver will evaluate current_app on import if outside of function.
    from flask import current_app
    pid_value = '10.13039/{0}'.format(doi_grant_code)
    try:
        _, record = Resolver(pid_type='grant', object_type='rec',
                             getter=Record.get_record).resolve(pid_value)
        return record
    except Exception:
        current_app.logger.error(
            'Grant {0} does not exists.'.format(pid_value), exc_info=True)
        raise


@jsonresolver.hookimpl
def jsonresolver_loader(url_map):
    """Resolve the OpenAIRE grant."""
    from flask import current_app
    url_map.add(Rule(
        '/grants/10.13039/<path:doi_grant_code>',
        endpoint=resolve_grant_endpoint,
        host=current_app.config['OPENAIRE_JSONRESOLVER_GRANTS_HOST']))
