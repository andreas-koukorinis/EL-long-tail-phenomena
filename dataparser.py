# -*- coding: utf-8 -*-

import classes
from rdflib import Graph, URIRef
import load_utils as utils
from lxml import etree
import glob

def load_article_from_nif_file(nif_file, limit=1000000, collection='wes2015'):
	"""
	Load a dataset in NIF format.
	"""
	g=Graph()
	g.parse(nif_file, format="n3")

	news_items=set()

	articles = g.query(
	""" SELECT ?articleid ?date ?string
	WHERE {
		?articleid nif:isString ?string .
		OPTIONAL { ?articleid <http://purl.org/dc/elements/1.1/date> ?date . }
	}
	LIMIT %d""" % limit)
	for article in articles:
		news_item_obj=classes.NewsItem(
			content=article['string'],
			identifier=article['articleid'], #"http://yovisto.com/resource/dataset/iswc2015/doc/281#char=0,4239",
			dct=article['date'],
			collection=collection
		)
		query=""" SELECT ?id ?mention ?start ?end ?gold
		WHERE {
			?id nif:anchorOf ?mention ;
			nif:beginIndex ?start ;
			nif:endIndex ?end ;
			nif:referenceContext <%s> .
			OPTIONAL { ?id itsrdf:taIdentRef ?gold . }
		} ORDER BY ?start""" % str(article['articleid'])
		qres_entities = g.query(query)
		for entity in qres_entities:
			gold_link=utils.getLinkRedirect(utils.normalizeURL(str(entity['gold'])))
			if gold_link.startswith('http://aksw.org/notInWiki'):
				gold_link='--NME--'
			page_rank=utils.computePR(gold_link)
			entity_obj = classes.EntityMention(
				begin_index=int(entity['start']),
				end_index=int(entity['end']),
				mention=str(entity['mention']),
				gold_link=gold_link,
				gold_pr=page_rank
			)
			news_item_obj.entity_mentions.append(entity_obj)
		news_items.add(news_item_obj)
	return news_items


def load_article_from_tsv_file(tsv_file):
	"""
	Load a dataset in TSV format.
	"""
	lines=open(tsv_file, 'r', encoding='utf-8')
	news_items=set()

	current_file=''
	current_topic=''
	content=[]
	for line in lines:
		if line.startswith('-DOCSTART-'):
			current_offset=0
			if current_file!="":
				news_item_obj.content = ' '.join(content)
				news_items.add(news_item_obj)
				content=[]
			# change current file
			current_file, current_topic=line.lstrip('-DOCSTART-').strip().split('\t')
			if 'testa' in current_file:
				collection='aidatesta'
			elif 'testb' in current_file:
				collection='aidatestb'
			else:
				collection='aidatrain'
			news_item_obj = classes.NewsItem(
				identifier=current_file,
				domain=current_topic,
				collection=collection
			)
		else:
			elements=line.split('\t')
			word=elements[0]
			content.append(word)
			if len(elements)>3 and elements[1]=='B':
				mention=elements[2]
				gold=utils.getLinkRedirect(elements[3].encode('utf-8').decode('unicode_escape'))
				page_rank=utils.computePR(gold)
				entity_obj = classes.EntityMention(
                         		begin_index=current_offset,
                                	end_index=current_offset + len(mention),
                                	mention=mention,
                                	gold_link=gold,
					gold_pr=page_rank
                        	)
				news_item_obj.entity_mentions.append(entity_obj)
			current_offset+=len(word)+1
	news_item_obj.content = ' '.join(content)
	news_items.add(news_item_obj)
	return news_items

def load_article_from_xml_files(location, collection='msnbc'):
	"""
	Load a dataset in XML format.
	"""
	news_items=set()
	for filename in glob.glob(location):
		parser = etree.XMLParser(recover=True)
		xml = etree.parse(filename, parser)
		news_item_obj = classes.NewsItem(
			identifier=filename,
			collection=collection
		)
		for entity_mention in xml.iterfind('/ReferenceInstance'):
			mention=entity_mention.find('SurfaceForm').text.strip()
			offset=int(entity_mention.find('Offset').text.strip())
			length=int(entity_mention.find('Length').text.strip())
			raw_gold=entity_mention.find('ChosenAnnotation').text
			gold_link=utils.getLinkRedirect(utils.normalizeURL(raw_gold))
			if utils.computePR(gold_link)==0:
				gold_link=None
			entity_obj = classes.EntityMention(
				begin_index=offset,
				end_index=offset + length,
				mention=mention,
				gold_link=gold_link
			)		
			news_item_obj.entity_mentions.append(entity_obj)
		news_items.add(news_item_obj)
	return news_items

#load_article_from_nif_file("data/wes2015-dataset-nif-1.2.rdf", 1)
#load_article_from_xml_files('data/WikificationACL2011Data/MSNBC/Problems/*')
