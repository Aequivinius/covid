import pandas as pd
import numpy
import urllib.request
import os
import json
from oger.ctrl.router import Router, PipelineServer

VOCABULARY = "CHEBI CL GO_BP GO_CC GO_MF MOP NCBITaxon PR SO UBERON"
VOCABULARIES = VOCABULARY.split()

def get_pmids():
	url = 'https://www.ncbi.nlm.nih.gov/research/coronavirus-api/export?'
	urllib.request.urlretrieve(url,'data/pmids.tsv')
	dataf = pd.read_csv('data/pmids.tsv', sep='\t', comment='#')
	dataf = dataf['pmid'][~dataf['pmid'].isin(['32150360', '32104909', '32090470'])]
	dataf.to_csv('data/pmids.txt', sep=' ', index=False, header=False)

def pmctsv_to_txt(inpath):
    dataf = pd.read_csv(inpath,header=0,delimiter='\t')
    dataf['PMCID'] = dataf['PMCID'].str.slice(3)
    dataf['PMCID'].replace("", numpy.nan, inplace=True)
    dataf.dropna(subset=['PMCID'], inplace=True)
    
    # this article is somehow not available on PMC
    dataf = dataf[dataf['PMCID'] != '7068758']

    outpath = os.path.join(os.path.dirname(inpath),'pmcids.txt')
    dataf['PMCID'].to_csv(outpath, index=False, header=False)

def conll_collection_to_jsons():
	pl = PipelineServer(Router())
	for v in VOCABULARIES:
		f = os.path.join('data/harmonised/', v + '.conll')

		collection = pl.load_one(f, 'conll')
		for document in collection:
			title = document[0].text
			pmid = document.id_
			directory = os.path.join('data/harmonised_json/',v)
			if not os.path.exists(directory):
				os.makedirs(directory)

			outfile = os.path.join(directory, pmid + '.json')
			with open(outfile, 'w', encoding='utf8') as g:
				pl.write(document, 'pubanno_json', g)
			with open(outfile, 'r+', encoding='utf8') as g:
				bad_json = json.load(g)
				bad_json['sourcedb'] = 'pubmed'
				bad_json['sourceid'] = pmid

				t = bad_json['text']
				tl = len(title)
				bad_json['text'] = t[:tl] + ' ' + t[tl:]
				good_json = bad_json
				g.seek(0)
				json.dump(good_json, g)
