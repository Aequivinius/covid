import pandas as pd
import urllib.request

from oger.ctrl.router import Router, PipelineServer
import glob
import os
import json

def get_pmids():
	url = 'https://www.ncbi.nlm.nih.gov/research/coronavirus-api/export?'
	urllib.request.urlretrieve(url,'data/pmids.tsv')
	dataf = pd.read_csv('data/pmids.tsv', sep='\t', comment='#')
	dataf = dataf['pmid'][~dataf['pmid'].isin(['32150360', '32104909', '32090470'])]
	dataf.to_csv('data/pmids.txt', sep=' ', index=False, header=False)
	
def conll_to_json():
	pl = PipelineServer(Router())
	
	title = False
	
	for f in glob.glob('data/oger/*/*.conll'):
		print(f)
		pmid = os.path.splitext(os.path.basename(f))[0]
		if not pmid.startswith('collection'):
	
			doc = pl.load_one(f, 'conll')
			try:
				title = doc[0][0].text
			except:
				i=0
	
			category = os.path.split(os.path.dirname(f))[-1]
			directory = os.path.join('data/oger_json/', category)
			if not os.path.exists(directory):
				os.makedirs(directory)
	
			outfile = os.path.join(directory, pmid + '.json')
			with open(outfile, 'w', encoding='utf8') as g:
				pl.write(doc, 'pubanno_json', g)
			with open(outfile, 'r+', encoding='utf8') as g:
				bad_json = json.load(g)
				bad_json['sourcedb'] = 'PubMed'
				bad_json['sourceid'] = pmid
	
				if title:
					t = bad_json['text']
					tl = len(title)
					bad_json['text'] = t[tl:] + ' ' + t[:tl].strip()
					
				good_json = bad_json
				g.seek(0)
				json.dump(good_json, g)

	
if __name__== "__main__":
  conll_to_json()