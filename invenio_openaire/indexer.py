# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Record modification prior to indexing."""

from __future__ import absolute_import, print_function

from elasticsearch import VERSION as ES_VERSION


def indexer_receiver(sender, json=None, record=None, index=None,
                     **dummy_kwargs):
    """Connect to before_record_index signal to transform record for ES."""
    if index and index.startswith('grants-'):
        code = json.get('code')
        suggestions = [
                code,
                json.get('acronym'),
                json.get('title')
            ]
        if code and "_" in code:
            suggestions.extend(code.split("_"))
        if ES_VERSION[0] == 2:
            # Generate suggest field
            json['suggest'] = {
                'input': [s for s in suggestions if s],
                'output': json['title'],
                'context': {
                    'funder': [json['funder']['doi']]
                },
                'payload': {
                    'id': json['internal_id'],
                    'legacy_id': (json['code'] if json.get('program') == 'FP7'
                                  else json['internal_id']),
                    'code': json['code'],
                    'title': json['title'],
                    'acronym': json.get('acronym'),
                    'program': json.get('program'),
                },
            }

        elif ES_VERSION[0] > 2:
            # Generate suggest field
            json['suggest'] = {
                'input': [s for s in suggestions if s],
                'contexts': {
                    'funder': [json['funder']['doi']]
                }
            }
            json['legacy_id'] = json['code'] if json.get('program') == 'FP7' \
                else json['internal_id']

    elif index and index.startswith('funders-'):
        suggestions = json.get('acronyms', []) + [json.get('name')]
        if ES_VERSION[0] == 2:
            # Generate suggest field
            json['suggest'] = {
                'input': [s for s in suggestions if s],
                'output': json['name'],
                'payload': {
                    'id': json['doi']
                },
            }

        elif ES_VERSION[0] > 2:
            json['suggest'] = {
                'input': [s for s in suggestions if s],
            }
