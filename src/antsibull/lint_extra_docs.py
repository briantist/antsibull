# coding: utf-8
# Author: Felix Fontein <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2021
"""Lint extra collection documentation in docs/docsite/."""

import json
import os
import os.path
import re
import typing as t

import docutils.utils
import rstcheck

from .extra_docs import (
    find_extra_docs,
    lint_required_conditions,
    load_extra_docs_index,
    ExtraDocsIndexError,
)
from .yaml import load_yaml_file


_RST_LABEL_DEFINITION = re.compile(r'''^\.\. _([^:]+):''')


def load_collection_name(path_to_collection: str) -> str:
    '''Load collection name (namespace.name) from collection's galaxy.yml.'''
    manifest_json_path = os.path.join(path_to_collection, 'MANIFEST.json')
    if os.path.isfile(manifest_json_path):
        with open(manifest_json_path, 'rb') as f:
            manifest_json = json.load(f)
        # pylint:disable-next=consider-using-f-string
        collection_name = '{namespace}.{name}'.format(**manifest_json['collection_info'])
        return collection_name

    galaxy_yml_path = os.path.join(path_to_collection, 'galaxy.yml')
    if os.path.isfile(galaxy_yml_path):
        galaxy_yml = load_yaml_file(galaxy_yml_path)
        # pylint:disable-next=consider-using-f-string
        collection_name = '{namespace}.{name}'.format(**galaxy_yml)
        return collection_name

    raise Exception(f'Cannot find files {manifest_json_path} and {galaxy_yml_path}')


# pylint:disable-next=unused-argument
def lint_optional_conditions(content: str, path: str, collection_name: str
                             ) -> t.List[t.Tuple[int, int, str]]:
    '''Check a extra docs RST file's content for whether it satisfied the required conditions.

    Return a list of errors.
    '''
    results = rstcheck.check(
        content, filename=path,
        report_level=docutils.utils.Reporter.WARNING_LEVEL)
    return [(result[0], 0, result[1]) for result in results]


def lint_collection_extra_docs_files(path_to_collection: str
                                     ) -> t.List[t.Tuple[str, int, int, str]]:
    try:
        collection_name = load_collection_name(path_to_collection)
    except Exception:  # pylint:disable=broad-except
        return [(
            path_to_collection, 0, 0,
            'Cannot identify collection with galaxy.yml or MANIFEST.json at this path')]
    result = []
    all_labels = set()
    docs = find_extra_docs(path_to_collection)
    for doc in docs:
        try:
            # Load content
            with open(doc[0], 'r', encoding='utf-8') as f:
                content = f.read()
            # Rstcheck
            errors = lint_optional_conditions(content, doc[0], collection_name)
            result.extend((doc[0], line, col, msg) for (line, col, msg) in errors)
            # Lint labels
            labels, errors = lint_required_conditions(content, collection_name)
            all_labels.update(labels)
            result.extend((doc[0], line, col, msg) for (line, col, msg) in errors)
        except Exception as e:  # pylint:disable=broad-except
            result.append((doc[0], 0, 0, str(e)))
    index_path = os.path.join(path_to_collection, 'docs', 'docsite', 'extra-docs.yml')
    try:
        _, errors = load_extra_docs_index(index_path)
        result.extend((index_path, 0, 0, error) for error in errors)
    except ExtraDocsIndexError as exc:
        if len(docs) > 0:
            # Only report the missing index_path as an error if we found documents
            result.append((index_path, 0, 0, str(exc)))
    return result
