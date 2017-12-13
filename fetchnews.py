#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib.request
from bs4 import BeautifulSoup
from estnltk import Text
import MySQLdb, re, logging

def analyzeText(in_text, n_id, db, cursor):
	
	text = Text(in_text)
	
	sentence_count = 0
	count = 0
	for named_entity in text.named_entities:
		ne_words = named_entity.split()
		orig_words = text.named_entity_texts[count].split()

		
		word_count = 0
		out_entity = u''
		for ne_word in ne_words:
			if (word_count > len(orig_words)-1 ):
				break
			if (word_count):
				out_entity = "%s " % (out_entity)
			#last word  
			if (word_count == (len( ne_words )-1) ):
				new_word = ne_word
				if ( orig_words[word_count].isupper() ):
					new_word = new_word.upper()
				elif ( len(orig_words[word_count]) > 1 and orig_words[word_count][1].isupper() ):
					new_word = new_word.upper()
				elif ( orig_words[word_count][0].isupper() ):
					new_word = new_word.title()
				#Jevgeni Ossinovsk|Ossinovski
				if (out_entity and new_word.find('|') > 0 ):
					word_start = out_entity
					out_ent2 = ''
					for word_part in new_word.split('|'):
						if (out_ent2):
							out_ent2 = "%s|" % (out_ent2)
						out_ent2 = "%s%s%s" % (out_ent2, word_start, word_part)
					out_entity = out_ent2
				else:
					out_entity = "%s%s" % (out_entity, new_word)
			
			else:
				out_entity = "%s%s" % (out_entity, orig_words[word_count])
			
			word_count += 1
		
		ne_endpos = text.named_entity_spans[count][1]
		while (ne_endpos > text.sentence_ends[sentence_count]):
			sentence_count += 1
		
		## Rupert Colville'i
		if ( out_entity.find("'") > 0 ):
			out_entity = re.sub(u"^(.+?)\'\w*", u"\\1", out_entity)
		w_type = text.named_entity_labels[count]
		w_id = insertWord(db, cursor, out_entity, w_type)
		insertInnews(db, cursor, n_id, w_id)

		
		count += 1
	

def getNewsId(db, cursor, url):

	result = None
	sql = "SELECT n_id FROM news \
       WHERE (n_url = %s)"
	try:
		# Execute the SQL command
		cursor.execute(sql, (url,))
		result = cursor.fetchone()
		if (result):
			return result[0]
	except:
		raise
		return
	return result
       
def insertNews(db, cursor, url, title, n_date):
	if (url):
		sql = "INSERT INTO news(n_url, \
         n_title, n_date) \
         VALUES (%s, %s, %s )" 

		try:
			# Execute the SQL command
			cursor.execute(sql, (url, title, n_date))
			# Commit your changes in the database
			db.commit()
		except:
			# Rollback in case there is any error
			db.rollback()
			raise
			return

	return cursor.lastrowid

def getWordId(db, cursor, w_text):

	result = None
	sql = "SELECT w_id FROM words \
       WHERE (w_text = %s)" 
	try:
		# Execute the SQL command
		cursor.execute(sql, (w_text,))
		result = cursor.fetchone()
		if (result):
			return result[0]
	except:
		raise
		return
	return result

def insertInnews(db, cursor, n_id, w_id):
	if (n_id and w_id):

		n_id = int(n_id)
		w_id = int(w_id)
		sql = "UPDATE innews SET i_count = i_count+1 \
                          WHERE (n_id = %s AND w_id = %s)" 
		
		try:
			# Execute the SQL command
			cursor.execute(sql, (n_id, w_id))
			# Commit your changes in the database
			db.commit()
		except:
			# Rollback in case there is any error
			db.rollback()
			raise
			return
		if (not cursor.rowcount):

			sql = "INSERT INTO innews(n_id, \
            w_id, i_count) \
            VALUES (%s, %s, 1 )" 
			try:
				# Execute the SQL command
				cursor.execute(sql, (n_id, w_id))
				# Commit your changes in the database
				db.commit()
			except:
				# Rollback in case there is any error
				db.rollback()
				raise
				return


	return True

def insertWord(db, cursor, w_text, w_type):
	if (w_text):
		w_id = getWordId(db, cursor, w_text)
		if (not w_id):
			sql = "INSERT INTO words(w_text, \
            w_type) \
            VALUES (%s, %s )" 
			try:
				# Execute the SQL command
				cursor.execute(sql, (w_text, w_type))
				# Commit your changes in the database
				db.commit()
				w_id = cursor.lastrowid
			except:
				# Rollback in case there is any error
				db.rollback()
				raise
				return

	return w_id

def getArticle(article_url, db, cursor):
	
	out_text = ''
	
	if (article_url):
		f = urllib.request.urlopen(article_url)
		html_data = f.read()
		
		soup = BeautifulSoup(html_data, "lxml")
		##<meta property="article:modified_time" content="2016-12-14T10:49:25+02:00" />
		mod_date = soup.find("meta",  property="article:modified_time")

		out_date = ''
		if (mod_date):

			matchDate = re.search("^(\d+-\d+-\d+)T(\d+:\d+:\d+)", mod_date["content"])
			if matchDate:
				out_date = "%s %s" % (matchDate.group(1), matchDate.group(2))
		
		#title
		title = ''
		m_title = soup.find("meta",  property="og:title")
		if (m_title):
			title = m_title["content"]
		
		art_text = soup.find("article") 
		
		n_id = getNewsId(db, cursor, article_url)
		#FIXME check also if n_date is changed
		if (not n_id):
			n_id = insertNews(db, cursor, article_url, title, out_date)

			for row in art_text.find_all("p"):
				out_text = "%s%s" % (out_text, row.text)

			analyzeText(out_text, n_id, db, cursor)
			return True
	
	return False

##
## main
##

logging.basicConfig(filename='fetchnews.log',level=logging.INFO)
logging.basicConfig(format='%(asctime)s %(message)s')

db = MySQLdb.connect(host="localhost",db="main_db",read_default_file="~/.my.cnf",charset='utf8')
cursor = db.cursor()

rss_url = 'http://uudised.err.ee/rss'
excl_cats = ['Viipekeelsed uudised', 'ETV uudistesaated', 'Ilm']

f = urllib.request.urlopen(rss_url)
rss_data = f.read()
soup = BeautifulSoup(rss_data, "xml")
news_count = 0

for rss_item in soup.find_all('item'):

	#print (rss_item.category.string)
	if (rss_item.category.string.strip() not in excl_cats):
		latest_link = rss_item.link.string
		#print(latest_link)
		n_id = getNewsId(db, cursor, latest_link)
		if (not n_id):
			if ( getArticle(latest_link, db, cursor) ):
				news_count += 1

logging.info ("Fetched %d news." % (news_count, ))

# disconnect from server
db.close()

