### GENERAL STUFF
   * move this all to clwork

#### RUNNING OGER
   * the .py script gets the most recent PMIDs; which are then read by OGER's config/common.ini.
   * OGER needs to be run for all the categories individually `oger run -s config/common.ini config/CL.ini -o ../data/output/CL/
`
   * This should be wrapped up in a little script
   * It produces an error that it is missing 3 articles (32150360, 32104909, 32090470, 32076224), but then produces annotations for the remaining 1904 / 1907 files.

### RUNNING BERT
   * It doesn't look like I can run this on gimli or idavoll; so let's get rattle access tomorrow
   * Meanwhile, it looks like BB has for every category an ID model and a span model, so that's one call for each.

`python3 biobert_predict.py \
	--do_predict=true \
	--input_text=../data/output/CL/doc123.conll \
	--tf_record=../data/output/bert/doc123.tf_record \
	--vocab_file=common/vocab.txt \
	--bert_config_file=common/bert_config.json \
	--init_checkpoint=models/CL-ids/model.ckpt-52714 \
	--data_dir=models/CL-ids \
	--output_dir=../data/output/bert/CL-ids \
	--configuration=ids`

### HARMONISE
   * Haven't looked at this yet. 
