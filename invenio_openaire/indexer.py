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

"""Record modification prior to indexing."""

from __future__ import absolute_import, print_function


def indexer_receiver(sender, json=None, record=None, index=None,
                     **dummy_kwargs):
    """Connect to before_record_index signal to transform record for ES."""
    # Inject timestamp into record.
    if index and index.startswith('grants-'):
        # Generate suggest field
        suggestions = [
            json.get('code'),
            json.get('acronym'),
            json.get('title')
        ]
        json['suggest'] = {
            'input': [s for s in suggestions if s],
            'output': json['title'],
            'context': {
                'funder': [json['funder']['doi']]
            },
            'payload': {
                'id': json['internal_id'],
                'legacy_id': (json['code'] if json.get('program') == 'FP7'
                              else json['internal_id'])
            },
        }
    elif index and index.startswith('funders-'):
        # Generate suggest field
        suggestions = json.get('acronyms', []) + [json.get('name')]
        json['suggest'] = {
            'input': [s for s in suggestions if s],
            'output': json['name'],
            'payload': {
                'id': json['doi']
            },
        }
