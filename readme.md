# OGER / BioBERT / PubAnnotation

### 1.1 General Pipeline

1. A little  script downloads the most recent PMIDs included in the LitCovid dataset and creates the necessary `data` directories. The whole dataset is then annotated for 10 different vocabularies:

```
CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
```

2. OGER is first called: It downloads the articles and annotates them. For every vocabulary, it generates one big `VOCABULARY.conll` file containing all the articles and annotations in `data/oger/`. 
3. BioBert preprocessed the articles, and then predicts spans and ids for each of the vocabularies (into `data/biobert/CHEBI-ids.labels` etc.)
4. The outputs of OGER and BB are harmonised using `harmonise.py`, split into individual articles and converted to `.json`. For every vocabulary, a `.tgz`-archive containing those `.json` files is produced (`data/harmonised_json/CHEBI.tgz`).
5. The archives can be manually uploaded to PubAnnotation.

### 1.2 `data` directory

```
data
|--- pmids # list of ids to download
|--- oger
     |--- CL.conll # most recent OGER annotations
     |--- CHEBI.conll
     |--- ...
|--- biobert
     |--- CHEBI-ids.labels
     |--- CHEBI-spans.labels
     |--- ...
|--- biobert_tokens.tf_record # preprocessing material
|--- harmonised_conll
     |--- CL.conll
     |--- CHEBI.conll
     |--- ...
|--- harmonised_json
     |--- CL
          |--- 123456789.json
          |--- ...
     |--- CL.tgz
     |--- ... 
```

### 2.1 Obtaining PMIDs

```bash
python -c 'import covid; covid.conll_collection_to_jsons()'
```

### 2.2 OGER

* adapt the `config/common.ini`file (or use the one here); especially set `conll_include = docid offsets`. Like this, the resulting `.conll` file will prefix every individual article with `#doc_id = 123456789`, which allows us later on to split the articles again so they can be uploaded to PubAnnotation.
* also, I remember that in one of the `config` files there was a small error, but I don't recall which one.

```bash
# pwd = oger
for v in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
echo 'Running OGER for' $v
mkdir ../data/oger/$v/
oger run -s config/common.ini config/$v.ini -o ../data/oger/$v/
done
```

```bash
# copy the files for easier navigation
# pwd = data
for v in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
collection=$(ls -t oger/$v/*.conll | head -n1)
cp $collection oger/$v.conll
done
```

### 2.3 BioBert

```bash
# preprocessing
# pwd = bert
python3 biobert_predict.py \
--do_preprocess=true \
--input_text=../data/oger/CL.conll \
--tf_record=../data/biobert_tokens.tf_record \
--vocab_file=common/vocab.txt
```

* The following commands take quite some time to execute (but don't need GPUs). The models have different suffixes as described here:

```
["CHEBI"]=52715 
["CL"]=52714 
["GO_BP"]=52715 
["GO_CC"]=52712 
["GO_MF"]=52710 
["MOP"]=52710 
["NCBITaxon"]=52710 
["PR"]=52720 
["SO"]=52714 
["UBERON"]=52717
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

mkdir ../data/biobert/$v-$s

python3 biobert_predict.py \
	--do_predict=true \
	--tf_record=../data/biobert_tokens.tf_record \
	--bert_config_file=common/bert_config.json \
	--init_checkpoint=models/$v-$s/model.ckpt-${vocabularies[$v]} \
	--data_dir=models/$v-$s \
	--output_dir=../data/biobert/$v-$s \
	--configuration=$s

done
done 
```

### 2.4 `harmonise.py`

* As described in the [Furrer paper](https://arxiv.org/pdf/2003.07424.pdf), different merging strategies perform best depending on the vocabulary.  

```bash
declare -A vocabularies=( [CHEBI]=spans-first [CL]=spans-first [GO_BP]=spans-first [GO_CC]=spans-first [GO_MF]=spans-first [MOP]=spans-first [NCBITaxon]=ids-first [PR]=spans-only [SO]=spans-first [UBERON]=spans-first )

for v in "${!vocabularies[@]}"
do
python harmonise.py -t data/harmonised_conll/$v.conll -o data/oger/$v.conll -b data/biobert_tokens/collection.tokens -i data/biobert/$v-ids.labels -s data/biobert/$v-spans.labels -m ${vocabularies[$v]}
```

### 2.5 Upload to PubAnnotation

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