# Predict CRAFT concepts with OGER+BioBERT

## OGER

Prepare input documents with OGER, as described [here](oger/README.md).

Running OGER serves two purposes:
- Format conversion. OGER produces 4-column CoNLL files that can be directly processed by the BioBERT script. As OGER supports many popular document formats, it is likely that no further preprocessing is needed.
- Dictionary-based concept recogntion. OGER annotates terms from given dictionaries, which are later merged with the BioBERT predictions.


## BioBERT

Run BioBERT for predicting IDs and/or spans, as described [here](biobert/README.md).

For every input document, two separate files with tokens and labels are written.
If you run both span and ID prediction, you might end up with four files, but the two token files should be identical.


## Harmonise

Merge predictions from OGER and BioBERT.

Choose a merge strategy: "spans-only", "spans-first", "ids-first", or "ids-only".
Run the Python script _harmonise.py_ with the files produced in the previous steps; see `python3 harmonise.py -h` for a list of all options.
