# coding: utf8

from io import BytesIO
import json
import urllib.parse
import urllib.request
from PIL import Image, ImageDraw, ImageFont
from random import randrange
import sqlite3
import textwrap

def word_is_okay(word):
	return word.replace("'", "").replace("-", "").isalnum() or \
		word == "," or \
		word == "." or \
		word == ":" or \
		word == "!" or \
		word == "?" or \
		word == "..."
		
def text_with_border(draw, x, y, b_color, f_color, text, font):
	try:
		draw.text((x+1, y), text, font = font, fill = b_color)
		draw.text((x-1, y), text, font = font, fill = b_color)
		draw.text((x, y+1), text, font = font, fill = b_color)
		draw.text((x, y-1), text, font = font, fill = b_color)
		draw.text((x, y), text, font = font, fill = f_color)
	except Exception:
		raise Exception

class MalooBot:
	def __init__(self, config_sql, config_api):
		self.db_name = config_sql["db_name"]
		self.customsearch_id = config_api["customsearch_id"]
		self.customsearch_key = config_api["customsearch_key"]
		self.imgur_key = config_api["imgur_key"]
		
	def generate_answer(self, sentence):
		sqldb = sqlite3.connect(self.db_name)
		sqlcursor = sqldb.cursor()

		words = sentence.split(" ")
		for word in words:
			if len(word) < 4:
				words.remove(word)
		nb_words_left  = len(words)
		if nb_words_left == 0:
			return self.generate_sentence([])
		elif nb_words_left == 1:
			id = 0
		else:	
			id = randrange(0, len(words))
		word = words[id]
		query = "SELECT word1, word2 FROM base WHERE (lower(word1)=lower('{0}') or lower(word2)=lower('{0}')) ORDER BY RANDOM() LIMIT 1".format(word.replace("'", "''"))
		sqlcursor.execute(query)
		rows = sqlcursor.fetchall()
		if len(rows) == 0:
			[word, next] = self.generate_stem()
		else:
			[word, next] = rows[0]

		return self.generate_sentence([word, next])
	
	def generate_sentence(self, stem=[]):
		if stem == []:
			stem = self.generate_stem()
			while len(stem[0]) < 2 and len(stem[1]) < 2:
				stem = self.generate_stem()
		seed1 = stem[0]
		seed2 = stem[1]
		sentence = "{} {}".format(seed1, seed2)

		sqldb = sqlite3.connect(self.db_name)
		sqlcursor = sqldb.cursor()
		
		word1 = seed1
		word2 = seed2
		# Right side
		for i in range(60):
			sqlcursor.execute("""SELECT next.word
						FROM base
						INNER JOIN next
						ON base.id = next.stem_id
						WHERE lower('{}') = lower(base.word1)
						AND lower('{}') = lower(base.word2)
						ORDER BY RANDOM() * probability DESC
						LIMIT 1""".format(word1.replace("'", "''"), word2.replace("'", "''")))
			rows = sqlcursor.fetchall()
			if len(rows) == 0:
				break
			word1 = word2.lower()
			word2 = rows[0][0].lower()
			
			if word2 == ",":
				sentence = sentence + ","
			elif word2 in [".", "?", "!"]:
				sentence = sentence + word2
				break
			else:
				sentence = sentence + " " + word2
		
		word1 = seed1
		word2 = seed2
		# Left side
		for i in range(30):
			sqlcursor.execute("""SELECT previous.word
						FROM base
						INNER JOIN previous
						ON base.id = previous.stem_id
						WHERE lower('{}') = lower(base.word1)
						AND lower('{}') = lower(base.word2)
						ORDER BY RANDOM() * probability DESC
						LIMIT 1""".format(word1.replace("'", "''"), word2.replace("'", "''")))
			rows = sqlcursor.fetchall()
			if len(rows) == 0:
				break
			word2 = word1.lower()
			word1 = rows[0][0].lower()

			if word1 == ",":
				sentence = ", " + sentence 
			elif word2 == ",":
				sentence = word1 + sentence
			elif word1 in [".", "?", "!"]:
				break
			else:
				sentence =  word1 + " " + sentence
				
		sqldb.commit()
		sqldb.close()
		
		return sentence
	
	def generate_stem(self, hint=""):
		sqldb = sqlite3.connect(self.db_name)
		sqlcursor = sqldb.cursor()

		if hint != "":
			query = "SELECT word1, word2 FROM base WHERE (lower('{0}') = lower(word1) or lower('{0}') = lower(word2)) ORDER BY RANDOM() LIMIT 1".format(hint.replace("'","''"))
		else:
			query = "SELECT word1, word2 FROM base ORDER BY RANDOM() LIMIT 1"
		sqlcursor.execute(query)
		rows = sqlcursor.fetchall()

		if len(rows) == 0:
			return self.generate_stem()	    
		stem1 = rows[0][0]
		stem2 = rows[0][1]
		
		sqldb.commit()
		sqldb.close()
		
		return [stem1, stem2]
		
	def learnfrom_sentence(self, sentence):
		sentence = sentence.replace("'", "''")
		sentence = sentence.replace(",", " , ")
		sentence = sentence.replace(".", " . ")
		sentence = sentence.replace("\n", "")
		sentence = sentence.replace("\r", "")
		sentence = sentence.replace("(", "")
		sentence = sentence.replace(")", "")
		sentence = sentence.replace("\"", "")
		sentence = sentence.replace(u"\xab", "")
		sentence = sentence.replace(u"\xbb", "")
		words = sentence.split()
		nb_of_words = len(words)
		if nb_of_words > 2:
			self.db_add_word_a(words[0], words[1], words[2])
			for i in range(nb_of_words-3):
				self.db_add_word_ba(words[i], words[i+1], words[i+2], words[i+3])
			self.db_add_word_b(words[nb_of_words-3], words[nb_of_words-2], words[nb_of_words-1])

	def get_image(self, query):
		url = "https://www.googleapis.com/customsearch/v1"
		id = self.customsearch_id
		key = self.customsearch_key
		# &fileType=jpg
		url = "{}?q={}&searchType=image&key={}&cx={}".format(url, urllib.parse.quote_plus(query), key, id)
		try:
			response = urllib.request.urlopen(url, timeout=5)
		except Exception:
			raise Exception
		data = response.read().decode("utf-8")
		result = json.loads(data)
		image_url = result['items'][0]['link'] # return the first image found on google images
		
		return image_url

	def upload_image(self, image_path):
		api_key = self.imgur_key
		imgur_url = "https://api.imgur.com/3/image.json"
		file = open(image_path, 'rb')
		binary_data = file.read()
		payload = {'image': binary_data,
						'type': 'file'}
		details = urllib.parse.urlencode(payload)
		url = urllib.request.Request(imgur_url, details.encode('ascii'))
		url.add_header("Authorization","Client-ID {}".format(api_key))
		try:
			response = urllib.request.urlopen(url, timeout=20).read().decode('utf8', 'ignore')
		except Exception:
			raise Exception
		j = json.loads(response)

		return j['data']['link']
		
	def generate_image(self, hint=""):
		stem = self.generate_stem(hint)
		query = stem[0] + " " + stem[1]
		sentence = self.generate_sentence(stem)
		try:
			image_url = self.get_image(query)
		except Exception:
			"L'image que Google m'a filé est 404 Not Found :("
		try:
			img = Image.open(BytesIO(urllib.request.urlopen(image_url).read()))
		except Exception:
			return "J'arrive pas à charger l'image, tant pis."
		img_w, img_h = img.size
		ratio = max(600 / img_w, 600 / img_h)
		img_w *= ratio
		img_h *= ratio
		img = img.resize((int(img_w), int(img_h)), Image.ANTIALIAS)
		draw = ImageDraw.Draw(img)
		font = ImageFont.truetype("./fonts/coolvetica.ttf", 30)
		text_block = textwrap.wrap(sentence, width = 40)
		pad = 10
		current_h = img_h / 10
		for line in text_block:
			text_w, text_h = draw.textsize(line, font=font)
			try:
				text_with_border(draw, (img_w-text_w)/2, current_h, (0,0,0,255), (255,255,0,255), line, font)
			except Exception:
				return "L'imprimante est bloquée, bourrage papier."
			current_h += text_h + pad
		
		img.save("./maloo.png")
		try:
			result_url = self.upload_image("./maloo.png")
		except Exception:
			return "Imgur ne veut pas me répondre :("
		
		return result_url
	
	def db_add_word_ba(self, prev, stem1, stem2, next):
		if not word_is_okay(prev) \
			or not word_is_okay(stem1) \
			or not word_is_okay(stem2) \
			or not word_is_okay(next):
			return

		sqldb = sqlite3.connect(self.db_name)
		sqlcursor = sqldb.cursor()
		
		sqlcursor.execute("INSERT OR IGNORE INTO base VALUES (null, '{}', '{}')".format(stem1, stem2))
		sqlcursor.execute("""SELECT id
							FROM base
							WHERE word1 = '{}'
							AND word2 = '{}'""".format(stem1, stem2))
		rows = sqlcursor.fetchall()
		stem_id = rows[0][0]		
		sqlcursor.execute("INSERT OR IGNORE INTO previous VALUES ({}, '{}', 1)".format(stem_id, prev))
		sqlcursor.execute("UPDATE previous SET probability = probability + 1 WHERE stem_id LIKE {}".format(stem_id))
		sqlcursor.execute("INSERT OR IGNORE INTO next VALUES ({}, '{}', 1)".format(stem_id, next))
		sqlcursor.execute("UPDATE next SET probability = probability + 5  WHERE stem_id LIKE {}".format(stem_id))
							
		sqldb.commit()
		sqldb.close()
	
	def db_add_word_a(self, stem1, stem2, next):
		if not word_is_okay(stem1) \
			or not word_is_okay(stem2) \
			or not word_is_okay(next):
			return

		sqldb = sqlite3.connect(self.db_name)
		sqlcursor = sqldb.cursor()
		
		sqlcursor.execute("INSERT OR IGNORE INTO base VALUES (null, '{}', '{}')".format(stem1, stem2))
		sqlcursor.execute("""SELECT id
							FROM base
							WHERE word1 = '{}'
							AND word2 = '{}'""".format(stem1, stem2))
		rows = sqlcursor.fetchall()
		stem_id = rows[0][0]
		sqlcursor.execute("INSERT OR IGNORE INTO next VALUES ({}, '{}', 1)".format(stem_id, next))
		sqlcursor.execute("UPDATE next SET probability = probability + 5 WHERE stem_id LIKE {}".format(stem_id))
							
		sqldb.commit()
		sqldb.close()
							
							
	def db_add_word_b(self, stem1, stem2, prev):
		if not word_is_okay(prev) \
			or not word_is_okay(stem1) \
			or not word_is_okay(stem2):
			return
			   
		sqldb = sqlite3.connect(self.db_name)
		sqlcursor = sqldb.cursor()
		
		sqlcursor.execute("INSERT OR IGNORE INTO base VALUES (null, '{}', '{}')".format(stem1, stem2))
		sqlcursor.execute("""SELECT id
							FROM base
							WHERE word1 = '{}'
							AND word2 = '{}'""".format(stem1, stem2))
		rows = sqlcursor.fetchall()
		stem_id = rows[0][0]
		sqlcursor.execute("INSERT OR IGNORE INTO previous VALUES ({}, '{}', 1)".format(stem_id, prev))
		sqlcursor.execute("UPDATE previous SET probability = probability + 5 WHERE stem_id LIKE {}".format(stem_id))
							
		sqldb.commit()
		sqldb.close()

	def db_count_base(self):
		sqldb = sqlite3.connect(self.db_name)
		sqlcursor = sqldb.cursor()

		sqlcursor.execute("SELECT COUNT(*) FROM base")
		(result,) = sqlcursor.fetchone()

		sqldb.commit()
		sqldb.close()

		return result    