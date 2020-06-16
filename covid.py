import pandas as pd
import numpy
import urllib.request
import os
import json
from oger.ctrl.router import Router, PipelineServer

VOCABULARY = "CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON"
VOCABULARIES = VOCABULARY.split()

PMID_URL = 'https://www.ncbi.nlm.nih.gov/research/coronavirus-api/export?'
BAD_PMIDS = ['32150360',
             '32104909',
             '32090470',
             '32296195',
             '32269354',
             '32238946',
             '32214268',
             '32188956',
             '32161394',
             '32076224',
             '32352270',
             '32352260',
             '32350480',
             '32333516',
             '32332940',
             '32332350',
             '32310612',
             '32310553',
             '32297402',
             '32297223',
             '32412216',
             '32410783',
             '32410779',
             '32407043', '32405025', '32404815', '32401466', '32401463',
             '32394184', '32383101', '32382471', '32378179', '32350846',
             '32341907', '32479040', '32474290', '32473452', '32454425',
             '32332323', '32282624', '32251136', '32243304', '32243302',
             '32086404', '32054798']

def get_pmids(outpath='data/ids/'):
    tsv_output = os.path.join(outpath, 'all_pmids.tsv')
    txt_output = os.path.join(outpath, 'all_pmids.txt')

    urllib.request.urlretrieve(PMID_URL, tsv_output)
    dataf = pd.read_csv(tsv_output, sep='\t', comment='#')
    dataf = dataf['pmid'][~dataf['pmid'].isin(BAD_PMIDS)]
    dataf.to_csv(txt_output, sep=' ', index=False, header=False)


def pmcods_to_txt(inpath='data/ids/PMID-PMCID_15062020.ods',
                  old='data/ids/old_pmcids.txt'):
    newf = pd.read_excel(inpath, engine="odf")
    newf = newf[['PMCID']]
    newf['PMCID'].replace("", numpy.nan, inplace=True)
    newf.dropna(subset=['PMCID'], inplace=True)
    newf['PMCID'] = newf['PMCID'].str.slice(3)
    outpath = os.path.join(os.path.dirname(inpath), 'new_pmcids.txt')
    newf['PMCID'].to_csv(outpath, index=False, header=False)

    oldf = pd.read_csv(old, header=None, names=["PMCID"])

    news = set(newf['PMCID'].astype(int))
    olds = set(oldf['PMCID'])

    diffs = news.difference(olds)

    # remove = [ '7068758'

    outpath = os.path.join(os.path.dirname(inpath), 'pmcids.txt')
    with open(outpath, "w") as g:
        g.write("\n".join(str(item) for item in diffs))

def pmctsv_to_txt(inpath):
    dataf = pd.read_csv(inpath,header=0,delimiter='\t')
    dataf['PMCID'] = dataf['PMCID'].str.slice(3)
    dataf['PMCID'].replace("", numpy.nan, inplace=True)
    dataf.dropna(subset=['PMCID'], inplace=True)

    # this article is somehow not available on PMC
    dataf = dataf[dataf['PMCID'] != '7068758']

    outpath = os.path.join(os.path.dirname(inpath),'pmcids.txt')
    dataf['PMCID'].to_csv(outpath, index=False, header=False)


def conll_collection_to_jsons(inpath='data/merged/collection.conll',
                              outpath='data/pubannotation',
                              sourcedb='pubmed'):
    pl = PipelineServer(Router())
    collection = pl.load_one(inpath, 'conll')
    for document in collection:
        title = document[0].text
        pmid = document.id_
        if not os.path.exists(outpath):
            os.makedirs(outpath)

        outfile = os.path.join(outpath, pmid + '.json')
        with open(outfile, 'w', encoding='utf8') as g:
            pl.write(document, 'pubanno_json', g)
        with open(outfile,'r+', encoding='utf8') as g:
            bad_json = json.load(g)
            bad_json['sourcedb'] = sourcedb
            good_json = bad_json
            g.truncate(0)
            g.seek(0)
            json.dump(good_json, g)


def get_naked_conll(inpath='oger/collection.conll',
                    outpath='data/collection.naked.conll'):
    pl = PipelineServer()
    coll = pl.load_one(inpath, 'conll')
    for s in coll.get_subelements('sentence'):
        s.entities.clear()
    with open(outpath, 'w') as f:
        pl.write(coll, 'conll', f, conll_include='docid offsets')

def conll_collection_to_txts(inpath='data/merged/collection.conll',
                             outpath='data/public/txt'):
    pl = PipelineServer(Router())
    collection = pl.load_one(inpath, 'conll')
    for document in collection:
        pmid = document.id_
        if not os.path.exists(outpath):
            os.makedirs(outpath)

        outfile = os.path.join(outpath, pmid + '.txt')
        with open(outfile, 'w', encoding='utf8') as g:
            pl.write(document, 'txt', g)


def bioc_to_brat(inpath='data/merged/collection.bioc.json',
                 outpath='data/merged/brat'):
    pl = PipelineServer()
    coll = pl.load_one(inpath, "bioc_json")
    for doc in coll:
        pl.export(doc, output_directory=outpath, export_format='brat')
