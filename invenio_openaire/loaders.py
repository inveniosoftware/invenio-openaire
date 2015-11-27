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
"""OpenAIRE loader functions.

None of the functions in this module create any objects in invenio-records.
Instead they handle loading, resolving and finally converting the local XML
datasets into final JSON that's to be stored using invenio_records.

The OpenAIRE loader comes in two variants: local loader from the pre-fetched
OpenAIRE dataset using SQLite database and direct remote loader using OAI-PMH
endpint.

Both FundRef dataset loaders rely on the locally stored dataset. The remote
loader also capable of fetching it from a remote location.
"""

from __future__ import absolute_import, print_function

import os
import sqlite3
import xml.etree.ElementTree as ET

import requests
from flask import current_app
from lxml import etree
from sickle import Sickle

from . import __path__ as current_package
from .errors import FunderNotFoundError


class JSONSchemaURLFormatter(object):
    """Formatter for '$schema' arguments in loaded JSONs."""

    def __init__(self, schemas_host=None, schemas_endpoint=None,
                 schema_file=None, schema_url=None):
        """Create a schema reference.

        Create the schema URL with host, endpoint and file, or set a fixed URL.
        Either (but not both at the same time) path to schema file is mandatory
        ('schema_file') or the absolute schema url ('schema_url').
        """
        assert (schema_file is not None) ^ (schema_url is not None), \
            "Either (but not both) 'schema_file' name or 'schema_url' are "
        "mandatory kwargs."

        self._schemas_host = schemas_host or \
            current_app.config['OPENAIRE_SCHEMAS_HOST']

        self._schemas_endpoint = schemas_endpoint or \
            current_app.config['OPENAIRE_SCHEMAS_ENDPOINT']

        self._schema_file = schema_file
        self.schema_url = schema_url or self._make_schema_url()

    def _make_schema_url(self):
        """Create the schema url from the host, endpoint and schema file."""
        return "http://{0}{1}/{2}".format(
            self._schemas_host, self._schemas_endpoint, self._schema_file)


class BaseOAIRELoader(object):
    """Base loader for the OpenAIRE dataset."""

    def __init__(self, source, funder_resolver=None, namespaces=None,
                 schema_formatter=None):
        """Initialize the loader."""
        self.source = source
        self.funder_resolver = funder_resolver or FundRefDOIResolver()
        self.namespaces = namespaces or \
            current_app.config['OPENAIRE_OAIPMH_NAMESPACES']
        self.schema_formatter = schema_formatter or JSONSchemaURLFormatter(
            schema_file=current_app.config['OPENAIRE_SCHEMAS_DEFAULT_GRANT'])

    def iter_grants(self):
        """Fetch and return the next grant in sequence."""
        return NotImplementedError  # pragma: no cover

    def get_all(self):
        """Fetch and return all grants."""
        return NotImplementedError  # pragma: no cover

    def get_text_node(self, tree, xpath_str):
        """Return a text node from given XML tree given an lxml XPath."""
        ret = tree.xpath(xpath_str, namespaces=self.namespaces)[0].text or ''
        return ret

    def get_subtree(self, tree, xpath_str):
        """Return a subtree given an lxml XPath."""
        return tree.xpath(xpath_str, namespaces=self.namespaces)

    def grantxml2json(self, tree):
        """Convert OpenAIRE grant XML into JSON."""
        oai_id = self.get_text_node(
            tree, '/oai:record/oai:header/oai:identifier')
        code = self.get_text_node(
            tree, '/oai:record/oai:metadata/oaf:entity/oaf:project/code')
        title = self.get_text_node(
            tree, '/oai:record/oai:metadata/oaf:entity/oaf:project/title')
        acronym = self.get_text_node(
            tree, '/oai:record/oai:metadata/oaf:entity/oaf:project/acronym')
        startdate = self.get_text_node(
            tree, '/oai:record/oai:metadata/oaf:entity/oaf:project/startdate')
        enddate = self.get_text_node(
            tree, '/oai:record/oai:metadata/oaf:entity/oaf:project/enddate')
        funder_node = self.get_subtree(
            tree, '/oai:record/oai:metadata/oaf:entity/oaf:project/'
                  'fundingtree/funder')
        subfunder_node = self.get_subtree(
            tree, '/oai:record/oai:metadata/oaf:entity/oaf:project/'
                  'fundingtree/funding_level_0')

        funder_id = self.get_text_node(funder_node[0], './id') \
            if funder_node else None
        subfunder_id = self.get_text_node(subfunder_node[0], './id') \
            if subfunder_node else None

        # Try to resolve the subfunder first, on failure try to resolve the
        # main funder, on failure raise an error.
        funder_doi_url = None
        if subfunder_id:
            funder_doi_url = self.funder_resolver.resolve_by_id(subfunder_id)
        if not funder_doi_url:
            if funder_id:
                funder_doi_url = self.funder_resolver.resolve_by_id(funder_id)
        if not funder_doi_url:
            raise FunderNotFoundError(funder_id, subfunder_id)

        funder_obj = {'$ref': funder_doi_url}
        funder_doi = FundRefDOIResolver.strip_doi_host(funder_doi_url)
        internal_id = "{0}/grants/{1}".format(funder_doi, code)

        ret_json = {
            '$schema': {'$ref': self.schema_formatter.schema_url},
            'internal_id': internal_id,
            'identifiers': {
                'oai_id': oai_id,
                'eurepo': '/eurepo/id',
            },
            'code': code,
            'title': title,
            'acronym': acronym,
            'startdate': startdate,
            'enddate': enddate,
            'funder': funder_obj,
        }
        return ret_json


class LocalOAIRELoader(BaseOAIRELoader):
    """Local OpenAIRE dataset loader.

    Load the OpenAIRE grant data from a pre-fetched local sqlite database.
    """

    def __init__(self, source=None, **kwargs):
        """Initialize the loader for local database."""
        super(LocalOAIRELoader, self).__init__(
            source or current_app.config['OPENAIRE_OAI_LOCAL_SOURCE'],
            **kwargs)
        self.db_connection = None

    def iter_grants(self):
        """Fetch records from the SQLite database."""
        self.db_connection = sqlite3.connect(self.source)
        n_grants = self.db_connection.cursor().execute(
            "SELECT COUNT(1) from record").fetchone()[0]
        result = self.db_connection.cursor().execute(
            "SELECT * FROM record"
        )
        for _ in range(int(n_grants)):
            raw_xml = result.fetchone()[0]
            tree = etree.fromstring(raw_xml)
            json = self.grantxml2json(tree)
            yield json
        self.db_connection.close()


class RemoteOAIRELoader(BaseOAIRELoader):
    """Remote OpenAIRE dataset loader.

    Fetch the OpenAIRE records from a remote OAI-PMH endpoint.
    """

    def __init__(self, source=None, **kwargs):
        """Initialize the loader for remote OAI-PMH access."""
        super(RemoteOAIRELoader, self).__init__(
            source or current_app.config['OPENAIRE_OAIPMH_ENDPOINT'],
            **kwargs)
        self.client = Sickle(self.source)

    def iter_grants(self):
        """Fetch grants from a remote OAI-PMH endpoint.

        Return the Sickle-provided generator object.
        """
        records = self.client.ListRecords(metadataPrefix='oaf',
                                          set='projects')
        for rec in records:
            tree = etree.fromstring(rec.raw)
            json = self.grantxml2json(tree)
            yield json


class GeoNamesResolver(object):
    """Resolver for the country codes from the GeoNames URL or ID."""

    def __init__(self, cc_fname=None, cc_data=None):
        """Initalize the GeoNames country code resolver.

        Provide the cc_data dictionary or create it from file:

        # cc_file:
        8502121,US
        8740971,US
        (...)

        cc_data = {'8502121':'US', '8740971':'CH', ... }
        """
        if cc_data:
            self.cc_data = cc_data
            self.cc_fname = None
        else:
            self.cc_fname = cc_fname or os.path.join(
                current_package[0],
                current_app.config['OPENAIRE_CC_SOURCE'])
            with open(self.cc_fname, 'r') as F:
                self.cc_data = {k: v[:-1] for k, v in (fi.split(',') for fi in
                                                       F.readlines())}

    def cc_from_id(self, geonames_id):
        """Resolve an ISO-3166 2-letter country code from GeoNames ID."""
        return self.cc_data[geonames_id]

    def cc_from_url(self, geonames_url):
        """Resolve an ISO-3166 2-letter country code from GeoNames URL."""
        geonames_id = geonames_url.split('/')[-2]
        return self.cc_from_id(geonames_id)


class BaseFundRefLoader(object):
    """Loader for the FundRef dataset file.

    Load the FundRef dataset from the file and convert all funders into python
    dictionaries.
    """

    def __init__(self, namespaces=None, cc_resolver=None,
                 schema_formatter=None):
        """Initialize the loader."""
        self.namespaces = namespaces or \
            current_app.config['OPENAIRE_FUNDREF_NAMESPACES']
        self.cc_resolver = cc_resolver or GeoNamesResolver()
        self.schema_formatter = schema_formatter or JSONSchemaURLFormatter(
            schema_file=current_app.config['OPENAIRE_SCHEMAS_DEFAULT_FUNDER'])

    def get_attrib(self, et_node, prefixed_attrib):
        """Get a prefixed attribute like 'rdf:resource' from ET node."""
        prefix, attrib = prefixed_attrib.split(':')
        return et_node.get('{{{0}}}{1}'.format(self.namespaces[prefix],
                                               attrib))

    def fundrefxml2json(self, node):
        """Convert a FundRef 'skos:Concept' node into JSON."""
        doi = FundRefDOIResolver.strip_doi_host(self.get_attrib(node,
                                                'rdf:about'))
        name = node.find('./skosxl:prefLabel/skosxl:Label/skosxl:literalForm',
                         namespaces=self.namespaces).text
        acronyms = [acronym.text for acronym in node.findall(
            './skosxl:altLabel/skosxl:Label/skosxl:literalForm',
            namespaces=self.namespaces)]
        parent_node = node.find('./skos:broader', namespaces=self.namespaces)
        if parent_node is None:
            parent = {}
        else:
            parent = {
                "$ref": self.get_attrib(parent_node, 'rdf:resource'),
            }
        country_elem = node.find('./svf:country', namespaces=self.namespaces)
        country_url = self.get_attrib(country_elem, 'rdf:resource')
        country_code = self.cc_resolver.cc_from_url(country_url)
        type_ = node.find('./svf:fundingBodyType',
                          namespaces=self.namespaces).text
        subtype = node.find('./svf:fundingBodySubType',
                            namespaces=self.namespaces).text
        country_elem = node.find('./svf:country', namespaces=self.namespaces)

        json_dict = {
            '$schema': {'$ref': self.schema_formatter.schema_url},
            'doi': doi,
            'name': name,
            'acronyms': acronyms,
            'parent': parent,
            'country': country_code,
            'type': type_,
            'subtype': subtype,
        }
        return json_dict

    def iter_funders(self):
        """Get a converted list of Funders as JSON dict."""
        root = self.doc_root
        funders = root.findall('./skos:Concept', namespaces=self.namespaces)
        for funder in funders:
            funder_json = self.fundrefxml2json(funder)
            yield funder_json


class LocalFundRefLoader(BaseFundRefLoader):
    """Load the FundRef dataset from a local file."""

    def __init__(self, namespaces=None, cc_resolver=None, source=None):
        """Initialize the local loader."""
        super(LocalFundRefLoader, self).__init__(
            namespaces=namespaces, cc_resolver=cc_resolver)
        self.source = source or \
            os.path.join(current_package[0],
                         current_app.config['OPENAIRE_FUNDREF_LOCAL_SOURCE'])
        self.doc_root = ET.parse(self.source).getroot()


class RemoteFundRefLoader(BaseFundRefLoader):
    """Load the FundRef dataset from a remote location."""

    def __init__(self, namespaces=None, cc_resolver=None, source=None):
        """Initialize the remote loader."""
        super(RemoteFundRefLoader, self).__init__(
            namespaces=namespaces, cc_resolver=cc_resolver)
        self.source = source or \
            current_app.config['OPENAIRE_FUNDREF_ENDPOINT']
        obj = requests.get(self.source, stream=True)
        raw_xml = obj.text
        self.doc_root = ET.fromstring(raw_xml)


class FundRefDOIResolver(object):
    """Resolve the FundRef funders by constant definitions."""

    def __init__(self, data=None):
        """Initialize the resolver."""
        fixed_funders = {
            'nhmrc_______::NHMRC': 'http://dx.doi.org/10.13039/501100000925',
            'ec__________::EC': 'http://dx.doi.org/10.13039/501100000780',
            'arc_________::ARC': 'http://dx.doi.org/10.13039/501100000923',
            'fct_________::FCT': 'http://dx.doi.org/10.13039/501100001871',
            'wt__________::WT': 'http://dx.doi.org/10.13039/100004440'
        }
        self.data = data or fixed_funders

    def resolve_by_id(self, funder_id):
        """Resolve the funder from the OpenAIRE funder id.

        If funder_id can be resolved, return a URI otherwise return None.
        """
        return self.data[funder_id] if (funder_id in self.data) else None

    @staticmethod
    def strip_doi_host(doi_url):
        """Strip DOI URL from the domain prefix."""
        return doi_url.replace('http://dx.doi.org/', '')

    def get_eurepo(self):
        """Resolve the eurepo identifier."""
