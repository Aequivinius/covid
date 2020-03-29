import pandas as pd
import urllib.request

def get_pmids():
	url = 'https://www.ncbi.nlm.nih.gov/research/coronavirus-api/export?'
	urllib.request.urlretrieve(url,'data/pmids.tsv')
	dataf = pd.read_csv('data/pmids.tsv', sep='\t', comment='#')
	s = dataf.iloc[:, 0]
	s.to_csv('data/pmids.txt', sep=' ', index=False, header=False)
	
if __name__== "__main__":
  get_pmids()