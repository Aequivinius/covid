#!/usr/bin/env python3
# coding: utf8

# Author: Lenz Furrer, 2019


"""
Postfilter for merging external annotations in CoNLL format.
"""


import re
import csv
import logging
from pathlib import Path

from oger.ctrl.router import PipelineServer, Router
from oger.doc.document import Entity
from oger.util.misc import tsv_format
from oger.util.stream import ropen


# The postfilters don't have access to the Router object of the main program,
# so it gets its own instance.
ROUTER = Router(settings=str(Path(__file__).with_suffix('.ini')))
SERVER = PipelineServer(ROUTER, lazy=True)

# All types used here (CL, MOP, SO, UBERON) use the same URI prefix.
URI_PREFIX = 'http://purl.obolibrary.org/obo/'


def merge(collection):
    """Include external annotations."""
    external = [SERVER.iter_load(str(path), 'conll')
                for path in Path(ROUTER.p.input_directory).glob('*.conll')]
    if not external:
        logging.warning('%s: no external annotations found', collection.id_)
        return
    logging.info('%s: merging annotations from %d collections',
                 collection.id_, len(external))

    # Align collections doc by doc. External docs might be out of order.
    docids = {d.id_: d for d in collection}
    print([path for path in Path(ROUTER.p.input_directory).glob('*.conll')])
    for ext in zip(*external):
        docid = ext[0].id_
        try:
            doc = docids.pop(docid)
        except KeyError:
            logging.error('%s: missing document: %s', collection.id_, docid)
            raise ValueError('missing document')
        if any(e.id_ != docid for e in ext):
            logging.error('%s: inconsistent IDs: %s',
                          collection.id_, [d.id_ for d in (doc, *ext)])
            raise ValueError('inconsistent IDs')

        # Align sentences. They must all be in the same order, but differences
        # are allowed wrt. sectioning and spacing.
        sentences = (d.get_subelements('Sentence') for d in (doc, *ext))
        for sent, *ext_sent in zip(*sentences):
            for e in ext_sent:
                if e.start != sent.start and _diff_no_ws(e.text, sent.text):
                    logging.error("%s, %s: sentence text doesn't match:\n%a\n%a",
                                  collection.id_, doc.id_, sent.text, e.text)
                    raise ValueError('sentence mismatch')
                sent.entities.extend(map(_restore_annotation, e.entities))
            sent.entities.sort(key=Entity.sort_key)

    # Sanity check: were all IDs used?
    for id_ in docids:
        logging.warning('%s: unmerged document: %s', collection.id_, id_)


def _diff_no_ws(a, b):
    """Strings differ even after stripping and unifying whitespace."""
    a, b = (re.sub(r'\s', ' ', s).strip() for s in (a, b))
    return a != b


def _restore_annotation(entity, terminology={}):
    """
    Restore missing information for this annotation.

    - Add the entity type.
    - Add the preferred name.
    - Add the ontology symbol (not used).
    - Add a prefix to the ID to make it a URI.
    """
    if not terminology:  # hack alert: default-arg caching trick
        _read_terminology(terminology)
    type_, pref, db = terminology[entity.cid]
    # uri = URI_PREFIX + entity.cid.replace(':', '_')
    uri = entity.cid
    entity.info = (type_, pref, db, uri, *entity.info[4:])
    return entity


def _read_terminology(destination):
    # Note: assume BTH format without header
    for params in ROUTER.p.recognizers:
        logging.info('loading external terminology: %s', params.path)
        with ropen(params.path, encoding='utf8', newline='') as f:
            rows = csv.reader(f, **tsv_format)
            for _, db, cid, _, pref, type_ in rows:
                type_ = type_.replace('/', '_')
                destination[cid] = type_, pref, db


def delete_duplicate_docs(collection):
    """Remove non-last occurrences of duplicate documents."""
    seen = set()
    _delete_docs(collection,
                 lambda d: d.id_ in seen or bool(seen.add(d.id_)),
                 'duplicate')


def delete_empty_docs(collection):
    """Remove documents without any text."""
    _delete_docs(collection,
                 lambda d: not any(d.get_subelements('Sentence')),
                 'empty')


def _delete_docs(collection, test, reason):
    n_del = 0
    # Traverse the collection backwards. Delete removable docs immediately.
    for i in reversed(range(len(collection.subelements))):
        if test(collection[i]):
            del collection.subelements[i]
            n_del += 1
    if n_del:
        logging.warning('%s: deleted %d %s documents',
                        collection.id_, n_del, reason)
