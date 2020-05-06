#!/bin/bash

home=$(pwd)

echo '0: Creating directories, backing up old data'
mv data data.$(date +'%d%m%Y')
mkdir data data/ids data/oger_pmc/ data/biobert_pmc/ data/harmonised_pmc/ data/pubannotation_pmc/ data/merged_pmc data/merged_pmc/brat/ data/public/


# 2: RUNNING OGER
cd $home/oger

for value in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
echo '2: Running OGER for' $value
time oger run -s config/common_pmc.ini config/$value.ini -o ../data/oger_pmc/$value
echo ''
done

# 2: data housekeeping
for value in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
collection=$(ls -t ../data/oger_pmc/$value/*.conll | head -n1)
cp $collection ../data/oger_pmc/$value.conll
rm -r ../data/oger_pmc/$value
done

# 3: RUNNING BIOBERT
cd $home/bert
echo '3.1: Preprocessing for BB'
time python3 biobert_predict.py \
--do_preprocess=true \
--input_text=../data/oger_pmc/CHEBI.conll \
--tf_record=../data/biobert_pmc.tf_record \
--vocab_file=common/vocab.txt

# refer to the readme.md for more information
# 1450
cd $home
for SERVER in asbru gimli idavoll vigrid
do
ssh $SERVER 'bash -s' < run_bb_pmc_$SERVER.sh
done

cd $home/data/biobert_pmc
echo '3: Moving BB files'
for v in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
for s in ids spans
do
echo $v-$s
mv $v-$s/biobert_tokens.labels $v-$s.labels
rm -r $v-$s
done
done


cd home
unset vocabularies
declare -A vocabularies=( [CHEBI]=spans-first [CL]=spans-first [GO_BP]=spans-first [GO_CC]=spans-first [GO_MF]=spans-first [MOP]=spans-first [NCBITaxon]=ids-first [PR]=spans-only [SO]=spans-first [UBERON]=spans-first )

for v in "${!vocabularies[@]}"
do
echo '4: Harmonising' $v
python harmonise.py -t data/harmonised_conll_pmc/$v.conll -o data/oger_pmc/$v.conll -b data/biobert_tokens_pmc.tokens -i data/biobert_pmc/$v-ids.labels -s data/biobert_pmc/$v-spans.labels -m ${vocabularies[$v]}
done

echo '5: Splitting and .tgz-ing'
python -c 'import covid; covid.conll_collection_to_jsons()'
for v in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
tar -czvf data/harmonised_json/$v.tgz data/harmonised_json/$v/
done
