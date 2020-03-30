#!/usr/bin/env python3
# coding: utf8

# Author: Lenz Furrer, 2020


"""
Harmonise predictions from BERT-ids, BERT-spans, and OGER.
"""


import csv
import argparse
import unicodedata
import itertools as it
from pathlib import Path
from typing import Tuple, Iterator


NIL = 'NIL'
TSV_FORMAT = dict(delimiter='\t', quotechar=None, lineterminator='\n')


def main():
    '''
    Run as script.
    '''
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        '-t', '--tgt-path', type=Path, required=True, metavar='PATH',
        help='path for output file')
    ap.add_argument(
        '-o', '--oger-pred', type=Path, required=True, metavar='PATH',
        help='input file containing documents in 4-column CoNLL format')
    ap.add_argument(
        '-b', '--bert-tokens', type=Path, required=True, metavar='PATH',
        help='input file containing BERT tokens')
    ap.add_argument(
        '-s', '--span-pred', type=Path, metavar='PATH',
        help='input file containing BERT span predictions')
    ap.add_argument(
        '-i', '--id-pred', type=Path, metavar='PATH',
        help='input file containing BERT ID predictions')
    ap.add_argument(
        '-m', '--merge-strategy', metavar='STRATEGY', default='ids-first',
        choices=('spans-only', 'spans-first', 'ids-first', 'ids-only',
                 'spans-alone'),
        help='strategy for span/ID predictions (default: %(default)s)')
    args = ap.parse_args()
    harmonise(**vars(args))


def harmonise(tgt_path: Path, oger_pred: Path, **kwargs) -> None:
    """
    Merge BERT predictions and restore document boundaries.
    """
    docs = _iter_input_docs(oger_pred)
    with PredictionMerger(**kwargs) as predictions:
        with tgt_path.open('w', encoding='utf8') as f:
            writer = csv.writer(f, **TSV_FORMAT)
            for docid, ref_rows in docs:
                writer.writerow([f'# doc_id = {docid}'])
                writer.writerows(predictions.iter_merge(ref_rows))


def _iter_input_docs(path):
    with open(path, encoding='utf8') as f:
        rows = csv.reader(f, **TSV_FORMAT)
        for docid, doc_rows in it.groupby(rows, DocIDTracker()):
            if docid is not DocIDTracker.DocumentSeparator:
                yield docid, doc_rows


class DocIDTracker:
    """Helper class for tracking IDs with it.groupby()."""

    DocumentSeparator = object()

    def __init__(self):
        self.docid = None

    def __call__(self, row):
        if row and row[0].startswith('# doc_id = '):
            self.docid = row[0].split('=', 1)[1].strip()
            return self.DocumentSeparator
        return self.docid


class PredictionMerger:
    """Handler for iteratively joining span/ID predictions."""

    def __init__(self, bert_tokens: Path,
                 span_pred: Path = None, id_pred: Path = None,
                 merge_strategy: str = 'ids-first'):
        self.spans = (_undo_wordpiece(bert_tokens, span_pred, 'spans')
                      if merge_strategy != 'ids-only' else None)
        self.ids = (_undo_wordpiece(bert_tokens, id_pred, 'ids')
                    if merge_strategy not in ('spans-only', 'spans-alone')
                    else None)
        method_name = f'_next_label_{merge_strategy}'.replace('-', '_')
        self._next_label = getattr(self, method_name)

    def close(self):
        """Make sure all files are closed."""
        for fmt in (self.spans, self.ids):
            if fmt is not None:
                if next(fmt, None) is not None:
                    raise ValueError('left-over predictions!')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.close()
        return False

    def iter_merge(self, ref_rows):
        """Iterate over merged rows."""
        for row in ref_rows:
            if not any(row):
                yield ()
                continue
            tok, start, end, feat = row
            feat = NIL if feat == 'O' else min(feat.split('-', 1)[1].split(';'))
            if len(tok) == 1 and self._is_control_char(tok):
                label = f'O-{NIL}'
            else:
                label = self._next_label(tok, feat)
            yield tok, start, end, label

    @staticmethod
    def _is_control_char(tok):
        """
        BERT's tokeniser deletes control chars and the replacement symbol.
        """
        return unicodedata.category(tok).startswith('C') or tok == '\ufffd'

    def _next_label_spans_alone(self, ref_tok, _):
        tag = self._next_prediction(self.spans, ref_tok)
        # Append dummy ID labels in order for
        # conll2standoff conversion to work properly.
        tag += '-NIL' if tag == 'O' else '-MISC'
        return tag

    def _next_label_spans_only(self, ref_tok, feat):
        tag = self._next_prediction(self.spans, ref_tok)
        if tag != 'O' and feat != NIL:
            label = f'{tag}-{feat}'
        else:
            label = f'O-{NIL}'
        return label

    def _next_label_ids_only(self, ref_tok, _):
        return self._next_prediction(self.ids, ref_tok)

    def _next_label_spans_first(self, ref_tok, feat):
        return self._next_label_both(ref_tok, feat, spans_first=True)

    def _next_label_ids_first(self, ref_tok, feat):
        return self._next_label_both(ref_tok, feat, spans_first=False)

    def _next_label_both(self, ref_tok, feat, spans_first):
        span = self._next_prediction(self.spans, ref_tok)
        id_ = self._next_prediction(self.ids, ref_tok)
        id_ = id_.split('-', 1)[1]  # strip leading I/O tag
        if span != 'O':
            if feat != NIL and (spans_first or id_ == NIL):
                id_ = feat
            elif id_ == NIL:
                span = 'O'
        elif id_ != NIL:
            span = 'I'  # default to I for non-O
        label = f'{span}-{id_}'
        return label

    def _next_prediction(self, pred, ref_tok):
        try:
            pred_tok, label = next(pred)
        except StopIteration:
            raise ValueError('predictions exhausted early!')
        self._assert_same_token(ref_tok, pred_tok)
        return label

    @staticmethod
    def _assert_same_token(ref_tok, pred_tok):
        if ref_tok == pred_tok:  # regular case
            return
        if pred_tok == '[UNK]':  # rare unknown token
            return
        if len(ref_tok) > 50 and ref_tok.startswith(pred_tok):  # long DNA seq.
            return
        raise ValueError(f'conflicting tokens: {ref_tok} vs. {pred_tok}')


def _undo_wordpiece(token_path: Path, pred_path: Path, label_format: str
                   ) -> Iterator[Tuple[str, str]]:
    """Iterate over pairs <token, label>."""
    ctrl_labels = _get_ctrl_labels(label_format)
    with token_path.open(encoding='utf8') as t, pred_path.open() as l:
        previous = None  # type: Tuple[str, str]
        for token, label in _restore_truncated(t, l):
            token, label = token.strip(), label.strip()
            if token.startswith('##'):
                # Merge word pieces.
                token = previous[0] + token[2:]
                # Ignore the predictions for this token.
                previous = token, previous[1]
            else:
                # A new word started. Yield what was accumulated.
                if previous is not None:
                    yield previous
                if token in CTRL_TOKENS:
                    # Silently skip control tokens.
                    previous = None
                else:
                    # Regular case.
                    label = ctrl_labels.get(label, label)  # replace with 'O'
                    previous = token, label
        if previous is not None:
            yield previous
        # Sanity check: all file iterators must be exhausted.
        if any(map(list, (t, l))):
            raise ValueError(f'unequal length: {token_path} {pred_path}')


def _restore_truncated(tokens, labels):
    """
    Handle space-separated lines in order to restore truncated sequences.
    """
    for tok_line, label in zip(tokens, labels):
        for token in tok_line.split():
            yield token, label
            # If there is more than one token on this line,
            # unset the label for the non-first iteration.
            label = 'X'


def _get_ctrl_labels(label_format):
    outside = {
        'spans': 'O',
        'ids': 'O-NIL'
    }[label_format]
    return dict.fromkeys(['[CLS]', '[SEP]', 'X'], outside)


CTRL_TOKENS = ('[CLS]', '[SEP]')


if __name__ == '__main__':
    main()
