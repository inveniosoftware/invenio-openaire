# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Errors for OpenAIRE harvesters and resolvers."""

from __future__ import absolute_import, print_function


class OAIRELoadingError(Exception):
    """Base class for OpenAIRE dataset loading errors."""


class FunderNotFoundError(OAIRELoadingError):
    """OpenAIRE grant funder could not be resolved error.

    Funder determined by funder_id and subfunder_id could not be matched
    with any of the available FundRef records.
    """

    def __init__(self, oai_id, funder_id, subfunder_id):
        """Initialize the exception."""
        self.oai_id = oai_id
        self.funder_id = funder_id
        self.subfunder_id = subfunder_id
