# OGER / BioBERT / PubAnnotation

All the outputs of this work go [here](https://pub.cl.uzh.ch/projects/COVID19/). This documentation only provides a superficial view on how the different scripts are called and how they depend on each other, for more precise calls see `run_all.sh`.

### 1.1 General Pipeline

1. A little  script downloads the most recent PMIDs included in the LitCovid dataset and creates the necessary `data` directories. The whole dataset is then annotated for the 10 different CRAFT vocabularies:

```
CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
```

2. OGER is first called: It downloads the articles and annotates them. For every vocabulary, it generates one big `data/oger/$VOCABULARY.conll` file containing all the articles and annotations.
3. BioBert preprocessed the articles, and then predicts spans and ids for each of the vocabularies (into `data/biobert/CHEBI-ids.labels` etc.)
4. The outputs of OGER and BB are harmonised using `harmonise.py`, split into individual articles and converted to `.json`. For every vocabulary, a `.tgz`-archive containing those `.json` files is produced (`data/harmonised_json/CHEBI.tgz`).
5. An additional merge step joins the 10 different vocabulary files, and searches the document again using a covid-specific, manually crafted dictionary (`oger/merge/covid19.tsv`)
6. The archives can be manually uploaded to PubAnnotation. Various export formats are then generated and placed in the respective directories so that they can be downloaded by the public [here](https://pub.cl.uzh.ch/projects/COVID19/).

### 1.2 `data` directory

```
data
|--- ids # list of ids to download
|--- oger (_pmc) # OGER annotations
     |--- CHEBI.conll
     |--- ...
|--- biobert (_pmc)
     |--- CHEBI-ids.labels
     |--- CHEBI-spans.labels
     |--- ...
|--- biobert(_pmc).tf_record / .tokens # preprocessing
|--- harmonised_conll (_pmc)
     |--- CL.conll
     |--- CHEBI.conll
     |--- ...
|--- harmonised_json
     |--- CL
          |--- 123456789.json
          |--- ...
     |--- CL.tgz
     |--- ...
|--- public # data that goes to be downloaded 
```

### 2.1 Obtaining PMIDs

```bash
python -c 'import covid; covid.get_pmids()'
```

### 2.2 OGER

* adapt the `config/common.ini`file (or use the one here); especially set `conll_include = docid offsets`. Like this, the resulting `.conll` file will prefix every individual article with `#doc_id = 123456789`, which allows us later on to split the articles again so they can be uploaded to PubAnnotation.
* also, I remember that in one of the `config` files there was a small error, but I don't recall which one.
* on our default development server, this takes about 50s per vocabulary.

```bash
# pwd = oger
for value in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
oger run -s config/common.ini config/$value.ini -o ../data/oger/$value
```

* Right now, this fails for NCBITaxon for some `lxml` library error.

### 2.3 BioBert

```bash
# preprocessing
# pwd = bert
python3 biobert_predict.py \
--do_preprocess=true \
--input_text=../data/oger/CL.conll \
--tf_record=../data/biobert.tf_record \
--vocab_file=common/vocab.txt
```

* Since the individual calls take quite some time this loop serves as a demonstration of what commands to run, but I wouldn't recommend running it as follows. The models of BB unfortunately have inconsistent suffixes.

```bash
declare -A vocabularies=( [CHEBI]=52715 [CL]=52714 [GO_BP]=52715 [GO_CC]=52712 [GO_MF]=52710 [MOP]=52710 [NCBITaxon]=52710 [PR]=52720 [SO]=52714 [UBERON]=52717 )

for v in "${!vocabularies[@]}"
do

for s in ids spans
do

echo "BB for" $v-$s
mkdir ../data/biobert/$v-$s

python3 biobert_predict.py \
	--do_predict=true \
	--tf_record=../data/biobert.tf_record \
	--bert_config_file=common/bert_config.json \
	--init_checkpoint=models/$v-$s/model.ckpt-${vocabularies[$v]} \
	--data_dir=models/$v-$s \
	--output_dir=../data/biobert/$v-$s \
	--configuration=$s

done
done 
```

* On our server there are also 4 scripts called `run_$SERVER.sh`, which are not uploaded to git. These can be called to run a bunch of screen processes according to the server's capacity.

### 2.4 `harmonise.py`

* As described in the [Furrer paper](https://arxiv.org/pdf/2003.07424.pdf), different merging strategies perform best depending on the vocabulary.  

```bash
declare -A vocabularies=( [CHEBI]=spans-first [CL]=spans-first [GO_BP]=spans-first [GO_CC]=spans-first [GO_MF]=spans-first [MOP]=spans-first [NCBITaxon]=ids-first [PR]=spans-only [SO]=spans-first [UBERON]=spans-first )

for v in "${!vocabularies[@]}"
do
python harmonise.py -t data/harmonised_conll/$v.conll -o data/oger/$v.conll -b data/biobert_tokens/collection.tokens -i data/biobert/$v-ids.labels -s data/biobert/$v-spans.labels -m ${vocabularies[$v]}
```
### 2.5 merging

* in `oger-settings-all.ini` , look at ` export_format = bioc_json` and add necessary output formats.

```bash
cd oger
oger run -s oger-settings-all.ini
```

### 2.6 Upload to PubAnnotation

* the harmonised `.conll`-collection files are split into individual articles and converted into `.json`, and `.tgz`-archived so they can be uploaded to PA.

```bash
python -c 'import covid; covid.conll_collection_to_jsons()'
```

```bash
for v in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
tar -czvf data/harmonised_json/$v.tgz data/harmonised_json/$v/
done
```

* The `.tgz` in `data/harmonised_json` you can manually upload on PubAnnotation at http://pubannotation.org/projects/YOUR-PROJECT/upload_annotations
  * Right now, it doesn't work with chrome
  * Make sure you select **ADD**
