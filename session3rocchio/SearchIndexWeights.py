"""
.. module:: SearchIndexWeight

SearchIndex
*************

:Description: SearchIndexWeight

	Performs a AND query for a list of words (--query) in the documents of an index (--index)
	You can use word^number to change the importance of a word in the match

	--nhits changes the number of documents to retrieve

:Authors: bejar
	

:Version: 

:Created on: 04/07/2017 10:56 

"""

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError

import argparse

from elasticsearch_dsl import Search
from elasticsearch_dsl.query import Q

__author__ = 'bejar'

nrounds=10 #vegades que s'aplica rocchio
R = 4 #maximum number of new terms
alpha = 1.0
beta = 1.0

def doc_count(client, index):
	"""
	Returns the number of documents in an index

	:param client:
	:param index:
	:return:
	"""
	return int(CatClient(client).count(index=[index], format='json')[0]['count'])


from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from elasticsearch.client import CatClient
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import Q

import argparse

import numpy as np

__author__ = 'bejar'

def search_file_by_path(client, index, path):
	"""
	Search for a file using its path

	:param path:
	:return:
	"""
	s = Search(using=client, index=index)
	q = Q('match', path=path)  # exact search in the path field
	s = s.query(q)
	result = s.execute()

	lfiles = [r for r in result]
	if len(lfiles) == 0:
		raise NameError(f'File [{path}] not found')
	else:
		return lfiles[0].meta.id


def document_term_vector(client, index, id):
	"""
	Returns the term vector of a document and its statistics a two sorted list of pairs (word, count)
	The first one is the frequency of the term in the document, the second one is the number of documents
	that contain the term

	:param client:
	:param index:
	:param id:
	:return:
	"""
	termvector = client.termvectors(index=index, id=id, fields=['text'],
									positions=False, term_statistics=True)

	file_td = {}
	file_df = {}

	if 'text' in termvector['term_vectors']:
		for t in termvector['term_vectors']['text']['terms']:
			file_td[t] = termvector['term_vectors']['text']['terms'][t]['term_freq']
			file_df[t] = termvector['term_vectors']['text']['terms'][t]['doc_freq']
	return sorted(file_td.items()), sorted(file_df.items())


def toTFIDF(client, index, file_id):
	"""
	Returns the term weights of a document

	:param file:
	:return:
	"""

	# Get the frequency of the term in the document, and the number of documents
	# that contain the term
	file_tv, file_df = document_term_vector(client, index, file_id)

	max_freq = max([f for _, f in file_tv])

	dcount = doc_count(client, index)

	tfidfw = []
	# w = tfdi * idfi
	#tfdi = w0 / maxfreqd
	#idfi = log2 (dcount/df)

	for (t, w),(_, df) in zip(file_tv, file_df):
		tfdi = w/max_freq
		idfi = np.log2(dcount/df)
		weight = tfdi * idfi
		tfidfw.append((t,weight))
		
	return normalize(tfidfw)

def print_term_weigth_vector(twv):
	"""
	Prints the term vector and the correspondig weights
	:param twv:
	:return:
	"""
	for t in twv:
		print(t)
	pass


def normalize(tw):
	"""
	Normalizes the weights in t so that they form a unit-length vector
	It is assumed that not all weights are 0
	:param tw:
	:return:
	"""
	total = 0
	for (t,w) in tw:
		total += w**2

	tw_normal = [(t,w/np.sqrt(total)) for (t,w) in tw]

	return tw_normal

def queryToDict(query):
	dict_query=[]
	for x in query:
		if '^' in x:
			key, weight = x.split('^')
			dict_query.append( (key,float(weight)) ) #sino el llegeix com a string
		else :
			dict_query.append((x,1.0))

	return  dict(normalize(dict_query))

def parseQuery(newQuery):
    query = []
    for (t,w) in newQuery:
        query.append( t + '^' + str(w) )
    return query

#retorna un vector normalizado de la forma (t,w) con los K terminos con mas peso
def rocchioNewQuery(dict_query,merged_d):

	for q in dict_query:
		dict_query[q] *= alpha

	for d in merged_d:
		merged_d[d] = beta * merged_d[d] 

	for q in dict_query:
		if q in merged_d:
			merged_d[q] = merged_d[q] + dict_query[q]
		else:
			merged_d[q]=dict_query[q]


	r = normalize( list(zip( merged_d.keys(), merged_d.values() )) )
	return sorted(r, key=lambda x: x[1],reverse=True)[:R] #tornem els R amb mes pes


 


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--index', default=None, help='Index to search')
	parser.add_argument('--nhits', default=10, type=int, help='Number of hits to return')
	parser.add_argument('--query', default=None, nargs=argparse.REMAINDER, help='List of words to search')

	args = parser.parse_args()

	index = args.index
	query = args.query
	print(query)
	nhits = args.nhits

	try:
		client = Elasticsearch()
		s = Search(using=client, index=index)
		merged_d = {} 
		if query is not None:
			for i in range(0,nrounds):
				q = Q('query_string',query=query[0])
				for i in range(1, len(query)):
					q &= Q('query_string',query=query[i])

				dict_query = queryToDict(query)

				s = s.query(q)
				response = s[0:nhits].execute()
				for r in response:  # only returns a specific number of results
					tw = toTFIDF(client, index,r.meta.id) #passem el document a tfidf
					# la funcio ja retorna un resultat normalitzat

					#afegim els termes de cada response a la mitjana
					for (t,w) in tw:
						if t in merged_d:
							merged_d[t] = merged_d[t] + w/nhits
						else:
							merged_d[t] = w/nhits

					#print(f'ID= {r.meta.id} SCORE={r.meta.score}')
					#print(f'PATH= {r.path}')
					#print(f'TEXT: {r.text[:50]}')
					#print('-----------------------------------------------------------------')

				newQuery = rocchioNewQuery(dict_query,merged_d)
				
				query = parseQuery(newQuery)
				#print(query)

		else:
			print('No query parameters passed')


		print(queryToDict(query))
		print (f"{response.hits.total['value']} Documents")

	except NotFoundError:
		print(f'Index {index} does not exists')

