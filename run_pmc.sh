#!/bin/bash

home=$(pwd)

echo '0: Creating directories, backing up old data'
mv data data.$(date +'%d%m%Y')
mkdir data data/ids data/oger_pmc/ data/biobert_pmc/ data/harmonised_pmc/ data/harmonised_json data/pubannotation_pmc/ data/merged_pmc data/merged_pmc/brat/ data/public/

# 2: RUNNING OGER
cd $home/oger

for value in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
echo '2: Running OGER for' $value
oger run -s config/common_pmc.ini config/$value.ini -o ../data/oger_pmc/$value
echo ''
done

# this file is necessary for later merge
cp ../data/oger_pmc/CHEBI/*.bioc_j  collection_pmc.bioc_json

# 2: data housekeeping
for value in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
collection=$(ls -t ../data/oger_pmc/$value/*.conll | head -n1)
cp $collection ../data/oger_pmc/$value.conll

rm -r ../data/oger_pmc/$value
done

# 3: RUNNING BIOBERT
cd $home/biobert
echo '3.1: Preprocessing for BB'
time python3 biobert_predict.py \
--do_preprocess=true \
--input_text=../data/oger_pmc/CHEBI.conll \
--tf_record=../data/biobert_pmc.tf_record \
--vocab_file=common/vocab.txt

# refer to the readme.md for more information
cd $home
for SERVER in 1 2 3 ...
do
ssh $SERVER 'bash -s' < run_bb_pmc_$SERVER.sh
done

cd $home/data/biobert_pmc
echo '3: Moving BB files'
cp -r biobert_pmc biobert_pmc.bkp
for v in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
for s in ids spans
do
echo $v-$s
mv $v-$s/biobert_pmc.labels $v-$s.labels
rm -r $v-$s
done
done


cd $home
unset vocabularies
declare -A vocabularies=( [CHEBI]=spans-first [CL]=spans-first [GO_BP]=spans-first [GO_CC]=spans-first [GO_MF]=spans-first [MOP]=spans-first [NCBITaxon]=ids-first [PR]=spans-only [SO]=spans-first [UBERON]=spans-first )

#zsh arrays
for v k in ${(kv)vocabularies}
do
echo '4: Harmonising' $v
python harmonise.py -t data/harmonised_pmc/$v.conll -o data/oger_pmc/$v.conll -b data/biobert_pmc.tokens -i data/biobert_pmc/$v-ids.labels -s data/biobert_pmc/$v-spans.labels -m $k
done



# 5: MERGING
echo '5: Merging'
cd $home/oger
# cp ../data/harmonised_pmc/CHEBI.conll collection_pmc.conll

oger run -s oger-pmc-settings.ini
mv ../data/merged_pmc/collection.json ../data/merged_pmc/collection.bioc.json

oger run -s oger-settings-pubannotation.ini
mv ../data/merged/collection.json ../data/merged/collection.pubannotation.json

# oger run -s oger-settings-eupmc.ini
# mv ../data/merged/collection.zip ../data/merged/collection.europmc.zip

# 6: DISTRIBUTION
echo '6: Splitting, .tgz-ing and moving to DL directories'
cd $home
python -c 'import covid; covid.conll_collection_to_jsons()'
tar -czvf data/pubannotation.tgz data/pubannotation/

cp data/merged/collection.bioc.json data/public/litcovid19.bioc.json
tar -czvf data/public/litcovid19.bioc.json.tgz data/public/litcovid19.bioc.json

cp data/merged/collection.tsv data/public/litcovid19.tsv
tar -czvf data/public/litcovid19.tsv.tgz data/public/litcovid19.tsv

python -c 'import covid; covid.conll_collection_to_txts()'
tar -czvf data/public/litcovid19.txt.tgz data/public/txt

python -c 'import covid; covid.bioc_to_brat()'
mv /mnt/shared/apaches/transfer/brat/brat_ontogene/data/LitCovid /mnt/shared/apaches/transfer/brat/brat_ontogene/data/LitCovid.$(date +'%d%m%Y')
cp data/merged/brat/* /mnt/shared/apaches/transfer/brat/brat_ontogene/data/LitCovid

mv /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid.$(date +'%d%m%Y')
cp data/public/* /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/





echo '5: Splitting and .tgz-ing'
python -c 'import covid; covid.conll_collection_to_jsons()'
for v in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
tar -czvf data/harmonised_json/$v.tgz data/harmonised_json/$v/
done
