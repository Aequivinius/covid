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
             '32297223']

def get_pmids(outpath='data/ids/'):
    tsv_output = os.path.join(outpath, 'pmids.tsv')
    txt_output = os.path.join(outpath, 'pmids.txt')

    urllib.request.urlretrieve(PMID_URL, tsv_output)
    dataf = pd.read_csv(tsv_output, sep='\t', comment='#')
    dataf = dataf['pmid'][~dataf['pmid'].isin(BAD_PMIDS)]
    dataf.to_csv(txt_output, sep=' ', index=False, header=False)


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
