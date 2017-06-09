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

"""OpenAIRE configuration file."""

from __future__ import absolute_import, print_function

from invenio_records_rest.facets import terms_filter
from invenio_records_rest.utils import allow_all

OPENAIRE_FUNDREF_LOCAL_SOURCE = 'data/fundref_registry.rdf'
OPENAIRE_FUNDREF_ENDPOINT = 'http://dx.doi.org/10.13039/fundref_registry'
OPENAIRE_CC_SOURCE = 'data/geonames2countrycodes_iso_3166.txt'
OPENAIRE_OAI_LOCAL_SOURCE = ''  # Large file that requires separate download
OPENAIRE_OAIPMH_ENDPOINT = 'http://api.openaire.eu/oai_pmh'
OPENAIRE_OAIPMH_DEFAULT_SET = 'projects'

OPENAIRE_FUNDREF_NAMESPACES = {
    'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    'xml': "http://www.w3.org/XML/1998/namespace",
    'dct': "http://purl.org/dc/terms/",
    'skos': "http://www.w3.org/2004/02/skos/core#",
    'skosxl': "http://www.w3.org/2008/05/skos-xl#",
    'svf': "http://data.fundref.org/xml/schema/grant/grant-1.2/",
    'rdfs': "http://www.w3.org/2000/01/rdf-schema#",
    'fref': "http://data.fundref.org/terms",
}

OPENAIRE_OAIPMH_NAMESPACES = {
    'oai': 'http://www.openarchives.org/OAI/2.0/',
    'oaf': 'http://namespace.openaire.eu/oaf',
}

OPENAIRE_SCHEMAS_HOST = 'inveniosoftware.org'
OPENAIRE_SCHEMAS_ENDPOINT = '/schemas'
OPENAIRE_SCHEMAS_DEFAULT_FUNDER = 'funders/funder-v1.0.0.json'
OPENAIRE_SCHEMAS_DEFAULT_GRANT = 'grants/grant-v1.0.0.json'
OPENAIRE_JSONRESOLVER_GRANTS_HOST = 'inveniosoftware.org'

OPENAIRE_GRANTS_SPECS = [
    'ARCProjects',
    'ECProjects',
    'FCTProjects',
    'MESTDProjects',
    'MZOSProjects',
    'NHMRCProjects',
    'NWOProjects',
    'WTProjects',
    'NSFProjects',
]


OPENAIRE_REST_ENDPOINTS = dict(
    frdoi=dict(
        pid_type='frdoi',
        pid_minter='openaire_funder_minter',
        pid_fetcher='openaire_funder_fetcher',
        list_route='/funders/',
        item_route='/funders/<pidpath(frdoi):pid_value>',
        search_index='funders',
        search_type=None,
        record_serializers={
            'application/json': (
                'invenio_records_rest.serializers:json_v1_response'),
        },
        search_serializers={
            'application/json': (
                'invenio_records_rest.serializers:json_v1_search'),
        },
        default_media_type='application/json',
        suggesters=dict(
            text=dict(completion=dict(
                field='suggest'
            ))
        ),
        read_permission_factory_imp=allow_all,
    ),
    grant=dict(
        pid_type='grant',
        pid_minter='openaire_grant_minter',
        pid_fetcher='openaire_grant_fetcher',
        list_route='/grants/',
        item_route='/grants/<pidpath(grant):pid_value>',
        search_index='grants',
        search_type=None,
        record_serializers={
            'application/json': (
                'invenio_records_rest.serializers:json_v1_response'),
        },
        search_serializers={
            'application/json': (
                'invenio_records_rest.serializers:json_v1_search'),
        },
        default_media_type='application/json',
        suggesters=dict(
            text=dict(completion=dict(
                field='suggest',
                context='funder',
            ))
        ),
        read_permission_factory_imp=allow_all,
    ),
)

OPENAIRE_REST_SORT_OPTIONS = dict(
    funders=dict(
        bestmatch=dict(
            fields=['-_score'],
            title='Best match',
            default_order='asc',
            order=1,
        ),
        name=dict(
            fields=['name'],
            title='Name',
            default_order='asc',
            order=2,
        ),
    ),
    grants=dict(
        bestmatch=dict(
            fields=['-_score'],
            title='Best match',
            default_order='asc',
            order=1,
        ),
        startdate=dict(
            fields=['startdate'],
            title='Start date',
            default_order='asc',
            order=2,
        ),
        enddate=dict(
            fields=['enddate'],
            title='End date',
            default_order='asc',
            order=2,
        ),
    )
)

#: Default sort for records REST API.
OPENAIRE_REST_DEFAULT_SORT = dict(
    grants=dict(query='bestmatch', noquery='bestmatch'),
    funders=dict(query='bestmatch', noquery='bestmatch'),
)

OPENAIRE_REST_FACETS = dict(
    funders=dict(
        aggs=dict(
            country=dict(
                terms=dict(field='country'),
            ),
            type=dict(
                terms=dict(field='type'),
            ),
        ),
        filters=dict(
            country=terms_filter('country'),
            type=terms_filter('type'),
        ),
    ),
    grants=dict(
        aggs=dict(
            funder=dict(
                terms=dict(field='funder.acronyms'),
            ),
        ),
        filters=dict(
            funder=terms_filter('funder.acronyms'),
        ),
    )
)
