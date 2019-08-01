# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Resolve JSON for FundRef funders."""

from __future__ import absolute_import, print_function

import jsonresolver
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record
from werkzeug.routing import Rule


@jsonresolver.hookimpl
def jsonresolver_loader(url_map):
    """Jsonresolver hook for funders resolving."""
    def endpoint(doi_code):
        pid_value = "10.13039/{0}".format(doi_code)
        _, record = Resolver(pid_type='frdoi', object_type='rec',
                             getter=Record.get_record).resolve(pid_value)
        return record

    pattern = '/10.13039/<doi_code>'
    url_map.add(Rule(pattern, endpoint=endpoint, host='doi.org'))
    url_map.add(Rule(pattern, endpoint=endpoint, host='dx.doi.org'))
