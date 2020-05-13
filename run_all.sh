#!/bin/bash

home=$(pwd)

echo '0: Creating directories, backing up old data'
mv data data.$(date +'%d%m%Y')
mkdir data data/ids/ data/oger/ data/biobert/ data/harmonised/ data/pubannotation/ data/merged data/merged/brat/ data/public/

echo '1: Downloading PMIDs'
python -c 'import covid; covid.get_pmids()'

# 2: RUNNING OGER
cd $home/oger

# during this step, it tends to fail a few times at first:
# OGER will whine about some articles not being available
# add them to the covid.py, and run step 1 again until
# OGER complains no more.

for value in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
echo '2: Running OGER for' $value
time oger run -s config/common.ini config/$value.ini -o ../data/oger/$value
echo ''

# 2: data housekeeping
collection=$(ls -t ../data/oger/$value/*.conll | head -n1)
cp $collection ../data/oger/$value.conll
rm -r ../data/oger/$value
done

# 3: RUNNING BIOBERT
cd $home/biobert
echo '3.1: Preprocessing for BB'
time python3 biobert_predict.py \
--do_preprocess=true \
--input_text=../data/oger/CHEBI.conll \
--tf_record=../data/biobert.tf_record \
--vocab_file=common/vocab.txt

# refer to the readme.md for more information
cd $home
for SERVER in 1 2 3 ...
do
ssh $SERVER 'bash -s' < run_bb_$SERVER.sh
done

# 3: data house keeping
cd $home
cp -r data/biobert data/biobert.bkp
for v in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
for s in spans ids
do
mv data/biobert/$v-$s/biobert.labels data/biobert/$v-$s.labels.tmp
rm -r data/biobert/$v-$s
mv data/biobert/$v-$s.labels.tmp data/biobert/$v-$s.labels
done
done

# 4: HARMONISING
cd $home
unset vocabularies
declare -A vocabularies=( [CHEBI]=spans-first [CL]=spans-first [GO_BP]=spans-first [GO_CC]=spans-first [GO_MF]=spans-first [MOP]=spans-first [NCBITaxon]=ids-first [PR]=spans-only [SO]=spans-first [UBERON]=spans-first )

#zsh style arrays
for v k in ${(kv)vocabularies}
do
echo '4: Harmonising' $v
python harmonise.py -t data/harmonised/$v.conll -o data/oger/$v.conll -b data/biobert.tokens -i data/biobert/$v-ids.labels -s data/biobert/$v-spans.labels -m $k
done


# 5: MERGING
echo '5: Merging'
cd $home/oger
cp ../data/harmonised/CHEBI.conll collection.conll

oger run -s oger-settings-all.ini
mv ../data/merged/collection.json ../data/merged/collection.bioc.json

oger run -s oger-settings-pubannotation.ini
mv ../data/merged/collection.json ../data/merged/collection.pubannotation.json
mv ../data/merged/collection.tgz ../data/merged/collection.pubannotation.tgz

oger run -s oger-settings-eupmc.ini
mv merged-eupmc/collection.conll ../data/merged/collection.europmc.conll
mv merged-eupmc/collection.json ../data/merged/collection.europmc.json
mv merged-eupmc/collection.zip ../data/merged/collection.europmc.zip
rm -r merged-eupmc


# 6: DISTRIBUTION
echo '6: Splitting, .tgz-ing and moving to DL directories'
cd $home
# this needs to be changed to utf-8, because otherwise it breaks
# for some articles on PubAnnotation
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
mkdir /mnt/shared/apaches/transfer/brat/brat_ontogene/data/LitCovid
cp data/merged/brat/* /mnt/shared/apaches/transfer/brat/brat_ontogene/data/LitCovid

mv /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid.$(date +'%d%m%Y')
mkdir /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/
cp data/public/* /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/