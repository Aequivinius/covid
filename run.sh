#!/bin/bash

home=$(pwd)

# Script cannot be run as is, since some steps take quite long
# Instead, copy & paste the individual steps as needed.

###########################
# 0: Setting up directories
###########################
echo '0: Creating directories, backing up old data'
mv data data.$(date +'%d%m%Y')
mkdir data data/ids/ data/oger/ data/biobert/ data/harmonised/ data/merged data/merged/brat/ data/public/ data/public/txt

# For PMC:
mkdir data data/ids data/oger_pmc/ data/biobert_pmc/ data/harmonised_pmc/ data/harmonised_json data/pubannotation_pmc/ data/merged_pmc data/merged_pmc/brat/ data/public/ data/public/txt

################
# 1: Getting IDs
################
echo '1: Downloading PMIDs'
python -c 'import covid; covid.get_pmids()'

# differences (change date to last time you ran the pipeline)
diff --new-line-format="" --unchanged-line-format="" data/ids/all_pmids.txt data.$(date +'%d%m%Y')/ids/all_pmids.txt > data/ids/pmids.txt

# for PMC, use the pmcods_to_txt() from covid.py

#################
# 2: RUNNING OGER
#################
cd $home/oger

# During this step, it tends to fail a few times at first:
# OGER will whine about some articles not being available.
# Add them to the covid.py in BAD_IDs, and delete them from
# pmids.txt until OGER complains no more. Usually, it's about
# 10 PMIDs that need removing.

for value in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
echo '2: Running OGER for' $value
time oger run -s config/common.ini config/$value.ini -o ../data/oger/$value
echo ''
done

for value in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
echo '2: Running OGER for' $value
time oger run -s config/common_pmc.ini config/$value.ini -o ../data/oger_pmc/$value
echo ''
done

# this file is necessary for later merge
cp ../data/oger/CHEBI/*.bioc_j  collection.bioc_json
cp ../data/oger_pmc/CHEBI/*.bioc_j  collection_pmc.bioc_json

# 2: data housekeeping
for value in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
collection=$(ls -t ../data/oger/$value/*.conll | head -n1)
cp $collection ../data/oger/$value.conll
rm -r ../data/oger/$value
done

for value in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
collection=$(ls -t ../data/oger_pmc/$value/*.conll | head -n1)
cp $collection ../data/oger_pmc/$value.conll
rm -r ../data/oger_pmc/$value
done

####################
# 3: RUNNING BIOBERT
####################

# If you take note of the number of predictions written in the preprocessing step
# You can get an idea of progress in the actuall processing step, which tends to
# take quite long.

cd $home/biobert
echo '3.1: Preprocessing for BB'
time python3 biobert_predict.py \
--do_preprocess=true \
--input_text=../data/oger/CHEBI.conll \
--tf_record=../data/biobert.tf_record \
--vocab_file=common/vocab.txt

# refer to the readme.md for more information
cd $home
for SERVER in asbru gimli idavoll vigrid
do
echo '3.2: Launching BB screens'
ssh $SERVER 'bash -s' < run_bb_$SERVER.sh
done

cd $home
for SERVER in 1 2 3 ...
do
ssh $SERVER 'bash -s' < run_bb_pmc_$SERVER.sh
done

# 3: data house keeping
cd $home/data
echo '3: Moving BB files'
cp -r biobert biobert.bkp
for v in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
for s in spans ids
do
mv biobert/$v-$s/biobert.labels biobert/$v-$s.labels
rm -r biobert/$v-$s
done
done


cd $home/data
echo '3: Moving BB files'
cp -r biobert_pmc biobert_pmc.bkp
for v in CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON
do
for s in ids spans
do
mv biobert_pmc/$v-$s/biobert_pmc.labels biobert_pmc/$v-$s.labels
rm -r biobert_pmc$v-$s
done
done

################
# 4: HARMONISING
################

cd $home
unset vocabularies
declare -A vocabularies=( [CHEBI]=spans-first [CL]=spans-first [GO_BP]=spans-first [GO_CC]=spans-first [GO_MF]=spans-first [MOP]=spans-first [NCBITaxon]=ids-first [PR]=spans-only [SO]=spans-first [UBERON]=spans-first )

#zsh style arrays
for v k in ${(kv)vocabularies}
do
echo '4: Harmonising' $v
python harmonise.py -t data/harmonised/$v.conll -o data/oger/$v.conll -b data/biobert.tokens -i data/biobert/$v-ids.labels -s data/biobert/$v-spans.labels -m $k
done

for v k in ${(kv)vocabularies}
do
echo '4: Harmonising' $v
python harmonise.py -t data/harmonised_pmc/$v.conll -o data/oger_pmc/$v.conll -b data/biobert_pmc.tokens -i data/biobert_pmc/$v-ids.labels -s data/biobert_pmc/$v-spans.labels -m $k
done

#################################
# 5: MERGING and COVID-ANNOTATION
#################################

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

# PMC
cp ../data/harmonised_pmc/CHEBI.conll collection_pmc.conll

oger run -s oger-pmc-settings.ini
mv ../data/merged_pmc/collection_pmc.json ../data/merged_pmc/collection_pmc.bioc.json

oger run -s oger-pmc-settings-pubannotation.ini
mv ../data/merged_pmc/collection_pmc.json ../data/merged_pmc/collection_pmc.pubannotation.json

# clean up
rm collection.conll collection_pmc.conll collection_pmc.bioc_json

#################
# 6: DISTRIBUTION
#################

echo '6: Splitting, .tgz-ing and moving to DL directories'
cd $home

# 6.0 backing up

# 6.1 PUBANNOTATION / PUBMED

# Possibly, update PA collection with data/ids/pmids.txt or pmcids.txt first
# Upload this to PubAnnotation
cp data/merged/collection.pubannotation.json data/collection.pubannotation.json

# 6.1 PUBANNOTATION / PMC

python -c 'import covid; covid.conll_collection_to_jsons(inpath="data/merged_pmc/collection_pmc.conll",outpath="data/pubannotation_pmc",sourcedb="PMC")'

# 6.2 BRAT / PUBMED

# Creating Brat files and adding new files to directory
python -c 'import covid; covid.bioc_to_brat()'
cp -r /mnt/shared/apaches/transfer/brat/brat_ontogene/data/LitCovid /mnt/shared/apaches/transfer/brat/brat_ontogene/data/LitCovid.$(date +'%d%m%Y')
cp data/merged/brat/* /mnt/shared/apaches/transfer/brat/brat_ontogene/data/LitCovid

# 6.2 BRAT / PMC

python -c 'import covid; covid.bioc_to_brat(inpath="data/merged_pmc/collection_pmc.bioc.json", outpath="data/merged_pmc/brat")'
cp -r /mnt/shared/apaches/transfer/brat/brat_ontogene/data/LitCovidPMC /mnt/shared/apaches/transfer/brat/brat_ontogene/data/LitCovidPMC.$(date +'%d%m%Y')
cp data/merged_pmc/brat/* /mnt/shared/apaches/transfer/brat/brat_ontogene/data/LitCovidPMC

# 6.3 File downloads : BioC / PubMed

cp data/merged/collection.bioc.json data/public/litcovid19.bioc.json
cp data/public/litcovid19.bioc.json /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/litcovid19.bioc/litcovid19.$(date +'%d%m%Y').bioc.json
tar -czvf /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/litcovid19.bioc.json.tgz /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/litcovid19.bioc

# 6.3 File downloads : BioC / PMC

cp /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid-PMC /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid-PMC.$(date +'%d%m%Y')

cp data/merged_pmc/collection_pmc.bioc.json data/public/covid19lit-pmc.bioc.json
cp data/public/covid19lit-pmc.bioc.json /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid-PMC/covid19lit-pmc.bioc.json/covid19lit-pmc.$(date +'%d%m%Y').bioc.json
tar -czvf /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid-PMC/covid19lit-pmc.bioc.json.tgz /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid-PMC/covid19lit-pmc.bioc.json

# 6.4 File downloads : TSV / PubMed

cp data/merged/collection.tsv data/public/litcovid19.tsv
cat data/public/litcovid19.tsv >> /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/litcovid19.tsv
tar -czvf /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/litcovid19.tsv.tgz /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/litcovid19.tsv

# 6.4 File downloads: TSV / PMC

cp data/merged_pmc/collection_pmc.tsv data/public/covid19lit-pmc.tsv
cat data/public/covid19lit-pmc.tsv >> /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid-PMC/covid19lit-pmc.tsv
tar -czvf /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid-PMC/covid19lit-pmc.tsv.tgz /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid-PMC/covid19lit-pmc.tsv

# 6.5 File downloads: TXT / PubMed

python -c 'import covid; covid.conll_collection_to_txts()'
cp data/public/txt/* /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/litcovid19.txt
tar -czvf /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/litcovid19.txt.tgz /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid/litcovid19.txt

# 6.5 File downloads: TXT / PMC

python -c 'import covid; covid.conll_collection_to_txts(inpath="data/merged_pmc/collection_pmc.conll",outpath="data/public/txt")'
cp data/public/txt/* /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid-PMC/covid19lit-pmc.txt
tar -czvf /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid-PMC/covid19lit-pmc.txt.tgz /mnt/storage/clfiles/projects/clresources/pub.cl.uzh.ch/public/https/projects/COVID19/LitCovid-PMC/covid19lit-pmc.txt

# Verify for EuroPMC
python -c 'import covid; covid.get_naked_conll()'
