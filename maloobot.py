# coding: utf8

"""
maloobot.py
--------

Here's the definition of the MalooBot class.
"""

from io import BytesIO
from random import randrange
import textwrap
import urllib.request

import sqlite3
from PIL import Image, ImageDraw, ImageFont

def word_is_okay(word):
    """ This function is checking for undesired words """
    return word.replace("'", "").replace("-", "").isalnum() or \
        word == "," or \
        word == "." or \
        word == ":" or \
        word == "!" or \
        word == "?" or \
        word == "..."

def text_with_border(draw, pos_x, pos_y, b_color, f_color, text, font):
    """ Needed to write text with borders of a different color """
    try:
        draw.text((pos_x + 1, pos_y), text, font=font, fill=b_color)
        draw.text((pos_x - 1, pos_y), text, font=font, fill=b_color)
        draw.text((pos_x, pos_y + 1), text, font=font, fill=b_color)
        draw.text((pos_x, pos_y - 1), text, font=font, fill=b_color)
        draw.text((pos_x, pos_y), text, font=font, fill=f_color)
    except Exception as ex:
        raise ex

class MalooBot:
    """
    This class is Maloo's core.
    It generates sentences, learn from sentences,
    goes on the internet (!) to find images, upload images
    and to post tweets.
    """
    def __init__(self, config_sql):
        self.sqldb = sqlite3.connect(config_sql["db_name"])

    def generate_answer(self, sentence):
        """ Generate an answer to the given message """
        sqlcursor = self.sqldb.cursor()

        words = sentence.split(" ")
        for word in words:
            if len(word) < 4:
                words.remove(word)
        nb_words_left = len(words)
        if nb_words_left == 0:
            return self.generate_sentence([])
        elif nb_words_left == 1:
            word_id = 0
        else:
            word_id = randrange(0, len(words))
        word = words[word_id]
        query = """SELECT word1, word2
                        FROM base
                        WHERE (lower(word1)=lower('{0}') or lower(word2)=lower('{0}'))
                        ORDER BY RANDOM()
                        LIMIT 1""".format(word.replace("'", "''"))
        sqlcursor.execute(query)
        rows = sqlcursor.fetchall()
        if len(rows) == 0:
            [word, next_word] = self.generate_stem()
        else:
            [word, next_word] = rows[0]

        return self.generate_sentence([word, next_word])

    def generate_sentence(self, stem=None):
        """ Generate a sentence.
        If a stem (a couple of word) is given, it is used to generate the sentence,
        otherwise, a random stem is generated """
        if stem is None:
            stem = self.generate_stem()
            while len(stem[0]) < 2 and len(stem[1]) < 2:
                stem = self.generate_stem()
        seed1 = stem[0]
        seed2 = stem[1]
        sentence = "{} {}".format(seed1, seed2)

        sqlcursor = self.sqldb.cursor()

        word1 = seed1
        word2 = seed2
        # Right side
        for _ in range(60):
            sqlcursor.execute("""SELECT next.word
                                FROM base
                                INNER JOIN next
                                ON base.id = next.stem_id
                                WHERE lower('{}') = lower(base.word1)
                                AND lower('{}') = lower(base.word2)
                                ORDER BY probability DESC
                                LIMIT 15""".format(word1.replace("'", "''"), \
                                                word2.replace("'", "''")))
            rows = sqlcursor.fetchall()
            nb_of_results = len(rows)
            if nb_of_results == 0:
                break
            next_id = randrange(0, nb_of_results)
            word1 = word2.lower()
            word2 = rows[next_id][0].lower()

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
        for _ in range(30):
            sqlcursor.execute("""SELECT previous.word
                                FROM base
                                INNER JOIN previous
                                ON base.id = previous.stem_id
                                WHERE lower('{}') = lower(base.word1)
                                AND lower('{}') = lower(base.word2)
                                ORDER BY probability DESC
                                LIMIT 15""".format(word1.replace("'", "''"), \
                                                word2.replace("'", "''")))
            rows = sqlcursor.fetchall()
            nb_of_results = len(rows)
            if nb_of_results == 0:
                break
            next_id = randrange(0, nb_of_results)
            word2 = word1.lower()
            word1 = rows[next_id][0].lower()

            if word1 == ",":
                sentence = ", " + sentence
            elif word2 == ",":
                sentence = word1 + sentence
            elif word1 in [".", "?", "!"]:
                break
            else:
                sentence = word1 + " " + sentence

        self.sqldb.commit()

        return sentence

    def generate_stem(self, hint=""):
        """ Returns a random couple of word from the database """
        sqlcursor = self.sqldb.cursor()

        if hint != "":
            query = """SELECT word1, word2
                            FROM base
                            WHERE (lower('{0}') = lower(word1) or lower('{0}') = lower(word2))
                            ORDER BY RANDOM()
                            LIMIT 1""".format(hint.replace("'", "''"))
        else:
            query = """SELECT word1, word2
                            FROM base
                            ORDER BY RANDOM()
                            LIMIT 1"""
        sqlcursor.execute(query)
        rows = sqlcursor.fetchall()

        if len(rows) == 0:
            return self.generate_stem()
        stem1 = rows[0][0]
        stem2 = rows[0][1]

        self.sqldb.commit()

        return [stem1, stem2]

    def learnfrom_sentence(self, sentence):
        """ Extracts words from a sentence to save it the database """
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

    def generate_image(self, image_url, font_name, hint=""):
        """ Very obscure shit, good exception generator """
        stem = self.generate_stem(hint)
        sentence = self.generate_sentence(stem)
        try:
            img = Image.open(BytesIO(urllib.request.urlopen(image_url).read()))
        except IOError as ex:
            raise ex
        font = ImageFont.truetype(font_name, 30)
        img_w, img_h = img.size
        ratio = max(600 / img_w, 600 / img_h)
        img_w *= ratio
        img_h *= ratio
        img = img.resize((int(img_w), int(img_h)), Image.ANTIALIAS)
        draw = ImageDraw.Draw(img)

        text_block = textwrap.wrap(sentence, width=40)
        current_h = img_h / 10
        for line in text_block:
            text_w, text_h = draw.textsize(line, font=font)
            try:
                text_with_border(draw, \
                                        (img_w-text_w) / 2, \
                                        current_h, \
                                        (0, 0, 0, 255), \
                                        (255, 255, 0, 255), \
                                        line, \
                                        font)
            except Exception as ex:
                raise ex
            current_h += text_h + 10

        img.save("./maloo.png")

        return "./maloo.png"

    def db_add_word_ba(self, prev_word, stem1, stem2, next_word):
        """ Used when: "^ ... prev_word STEM1 STEM2 next_word ... $" """
        if not word_is_okay(prev_word) \
            or not word_is_okay(stem1) \
            or not word_is_okay(stem2) \
            or not word_is_okay(next_word):
            return

        sqlcursor = self.sqldb.cursor()

        sqlcursor.execute("""INSERT OR IGNORE INTO base
                                    VALUES (null, '{}', '{}')""".format(stem1, stem2))
        sqlcursor.execute("""SELECT id
                                    FROM base
                                    WHERE word1 = '{}'
                                    AND word2 = '{}'""".format(stem1, stem2))
        rows = sqlcursor.fetchall()
        stem_id = rows[0][0]
        sqlcursor.execute("""INSERT OR IGNORE INTO previous
                                    VALUES ({}, '{}', 1)""".format(stem_id, prev_word))
        sqlcursor.execute("""UPDATE previous SET probability = probability + 1
                                    WHERE stem_id LIKE {}""".format(stem_id))
        sqlcursor.execute("""INSERT OR IGNORE INTO next
                                    VALUES ({}, '{}', 1)""".format(stem_id, next_word))
        sqlcursor.execute("""UPDATE next SET probability = probability + 5
                                    WHERE stem_id LIKE {}""".format(stem_id))

        self.sqldb.commit()

    def db_add_word_a(self, stem1, stem2, next_word):
        """ Used when: "^STEM1 STEM2 next_word ... $" """
        if not word_is_okay(stem1) \
            or not word_is_okay(stem2) \
            or not word_is_okay(next_word):
            return

        sqlcursor = self.sqldb.cursor()

        sqlcursor.execute("""INSERT OR IGNORE INTO base
                                    VALUES (null, '{}', '{}')""".format(stem1, stem2))
        sqlcursor.execute("""SELECT id
                            FROM base
                            WHERE word1 = '{}'
                            AND word2 = '{}'""".format(stem1, stem2))
        rows = sqlcursor.fetchall()
        stem_id = rows[0][0]
        sqlcursor.execute("""INSERT OR IGNORE INTO next
                                    VALUES ({}, '{}', 1)""".format(stem_id, next_word))
        sqlcursor.execute("""UPDATE next SET probability = probability + 5
                                    WHERE stem_id LIKE {}""".format(stem_id))

        self.sqldb.commit()

    def db_add_word_b(self, stem1, stem2, prev_word):
        """ Used when: "^ ... prev_word STEM1 STEM2$" """
        if not word_is_okay(prev_word) \
            or not word_is_okay(stem1) \
            or not word_is_okay(stem2):
            return

        sqlcursor = self.sqldb.cursor()

        sqlcursor.execute("""INSERT OR IGNORE INTO base
                                    VALUES (null, '{}', '{}')""".format(stem1, stem2))
        sqlcursor.execute("""SELECT id
                                    FROM base
                                    WHERE word1 = '{}'
                                    AND word2 = '{}'""".format(stem1, stem2))
        rows = sqlcursor.fetchall()
        stem_id = rows[0][0]
        sqlcursor.execute("""INSERT OR IGNORE INTO previous
                                    VALUES ({}, '{}', 1)""".format(stem_id, prev_word))
        sqlcursor.execute("""UPDATE previous SET probability = probability + 5
                                    WHERE stem_id LIKE {}""".format(stem_id))

        self.sqldb.commit()

    def db_count_base(self):
        """ Returns the number of couples that are in 'base' """
        sqlcursor = self.sqldb.cursor()

        sqlcursor.execute("SELECT COUNT(*) FROM base")
        (result,) = sqlcursor.fetchone()

        self.sqldb.commit()

        return result
