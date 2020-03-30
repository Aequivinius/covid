# Predict CRAFT concepts with BioBERT

## Installation

Requires TensorFlow 1.x.


## Run

Run BioBERT separately for every annotation set and label set (spans/IDs).
For example, for CL_EXT with ID labels, use the following command:

```
python3 biobert_predict.py \
	--do_predict=true \
	--input_text=input/doc123.conll \
	--tf_record=output/doc123.tf_record \
	--vocab_file=common/vocab.txt \
	--bert_config_file=common/bert_config.json \
	--init_checkpoint=models/CL_EXT-ids/model.ckpt-52714 \
	--data_dir=models/CL_EXT-ids \
	--output_dir=output/CL_EXT-ids \
	--configuration=ids
```

The file _input/doc123.conll_ is the output of OGER.
The labels are ignored; _biobert_predict.py_ really only looks at the first column of the CoNLL file.

The above command will write the following files:
- output/doc123.tf_record
- output/doc123.tokens
- output/CL_EXT-ids/doc123.labels

The last two are required for merging.

If you run many BioBERT models on the same (potentially long) document, it may be convenient to have a single source of truth for the .tokens/.tf_record file.
You can create these two files once with the `--do_preprocess` flag:

```
python3 biobert_predict.py \
	--do_preprocess=true \
	--input_text=input/doc123.conll \
	--tf_record=output/doc123.tf_record \
	--vocab_file=common/vocab.txt
```

... and then omit the `--input_text` and `--vocab_file` options in the subsequent prediction calls:

```
python3 biobert_predict.py \
	--do_predict=true \
	--tf_record=output/doc123.tf_record \
	...
```
