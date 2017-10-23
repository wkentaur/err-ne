#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb
import calendar
from datetime import date
import pywikibot, logging

def getData(db, cursor, start_date, end_date):
	if (isinstance(start_date, date) and isinstance(end_date, date)):
	
		assert (start_date <= end_date), "start_date is bigger than end_date!"
		
		sql = 'select n_url, n_title, n_date, w_text, w_type, i_count from news, words, innews \
        where ( (date(n_date) between %s and %s) and news.n_id = innews.n_id and words.w_id = innews.w_id) \
        order by n_date ASC, news.n_id ASC, w_type ASC, i_count DESC'

		out_text = u''

		try:
			# Execute the SQL command
			cursor.execute(sql,  (start_date, end_date))
			result = cursor.fetchall()
			if (result):
				out_text = u'{| class="wikitable" style="text-align: left;"'
			last_n_url = ''
			for row in result:
				new_word = ''
				(n_url, n_title, n_date, w_text, w_type, i_count) = row
				n_title = n_title.replace('|','')
				n_title = n_title.replace("\n",'')
				if (n_url != last_n_url):
					out_text = "%s\n|-\n| [%s %s]\n| %s\n|" % (out_text, n_url, n_title, n_date.strftime("%d.%m"))
				## LOC, ORG, PER
				if (w_text.find('|') > 0):
					new_word = "("
					for word_part in w_text.split('|'):
						new_word = "%s [[%s]]" % (new_word, word_part)
					new_word = "%s )" % (new_word, )
				else:
					new_word = "[[%s]]" % (w_text, )
				if (i_count > 2):
					new_word = "<big>%s</big>" % (new_word, )
				out_text = "%s %s" % (out_text, new_word )
				last_n_url = n_url
			out_text = "%s\n|}" % (out_text, )
		except:
			raise
	
	return out_text

##
## main
##

logging.basicConfig(filename='postwiki.log',level=logging.INFO)
logging.basicConfig(format='%(asctime)s %(message)s')

today = date.today()
wikiSite = pywikibot.getSite(u'et', u'wikipedia')
wikiPageName = u'Kasutaja:WikedKentaur/ERRi märksõnad/%s/%02d' % (today.year, today.month)
wikiPage = pywikibot.Page(wikiSite, wikiPageName)

db = MySQLdb.connect(host="localhost",db="main_db",read_default_file="~/.my.cnf",charset='utf8')
cursor = db.cursor()

mrange = calendar.monthrange(today.year,today.month)

start_date = date(today.year, today.month, 1)
end_date = date(today.year, today.month, mrange[1])

wText = getData(db, cursor, start_date, end_date)

wikiPage.put(wText)
logging.info ("Posted to wiki article: [[%s]]" % (wikiPageName, ))

# disconnect from server
db.close()
