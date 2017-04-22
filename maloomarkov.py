# coding: utf8

"""
maloomarkov.py
--------

Here's the definition of the MalooMarkov class.
"""

import textwrap
import urllib.request
from random import randrange
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

import maloosql

def word_is_okay(word):
    """
    This function is checking for undesired words
    """
    return word.replace("'", "").replace("-", "").isalnum() or \
        word == "," or \
        word == "." or \
        word == ":" or \
        word == "!" or \
        word == "?" or \
        word == "..."

def draw_text_with_border(draw, pos_x, pos_y, b_color, f_color, text, font):
    """
    Needed to write text with borders of a different color
    """
    try:
        draw.text((pos_x + 1, pos_y), text, font=font, fill=b_color)
        draw.text((pos_x - 1, pos_y), text, font=font, fill=b_color)
        draw.text((pos_x, pos_y + 1), text, font=font, fill=b_color)
        draw.text((pos_x, pos_y - 1), text, font=font, fill=b_color)
        draw.text((pos_x, pos_y), text, font=font, fill=f_color)
    except Exception as ex:
        raise ex

class MalooMarkov(object):
    """
    This class is Maloo's core.
    It generates sentences, learn from sentences,
    goes on the internet (!) to find images, upload images
    and to post tweets.
    """
    def __init__(self, sql_config):
        self.sql = maloosql.MalooSql(sql_config)

    def generate_answer(self, sentence):
        """
        Generate an answer to the given message
        """
        sane_sentence = self.sanatize_sentence(sentence)
        word = self.find_random_revelant_word(sane_sentence)
        if not word:
            answer = self.generate_sentence()
        else:
            stem = self.generate_stem(word)
            answer = self.generate_sentence(stem)

        return answer

    @staticmethod
    def find_random_revelant_word(sentence):
        words = sentence.split()
        for word in words:
            if len(word) < 4:
                words.remove(word)

        nb_words_left = len(words)
        if nb_words_left == 0:
            return None
        elif nb_words_left == 1:
            word_id = 0
        else:
            word_id = randrange(0, len(words))

        return words[word_id]

    def generate_sentence(self, stem=None):
        """
        Generate a sentence.
        If a stem (a couple of word) is given, it is used to generate the
        sentence, otherwise, a random stem is generated.
        """
        if not stem or len(stem) < 2:
            stem = self.generate_stem()
            while len(stem[0]) < 2 and len(stem[1]) < 2:
                stem = self.generate_stem()
        sentence = "%s %s" % stem
        # Right side
        word1, word2 = stem
        for _ in range(60):
            next_word = self.sql.find_next_word(word1, word2)
            if not next_word:
                break
            word1 = word2.lower()
            word2 = next_word
            sentence, complete = self.add_next_word_to_sentence(sentence,
                                                                next_word)
            if complete:
                break

        # Left side
        word1, word2 = stem
        for _ in range(30):
            prev_word = self.sql.find_previous_word(word1, word2)
            if not prev_word:
                break
            word2 = word1.lower()
            word1 = prev_word
            sentence, complete = self.add_previous_word_to_sentence(sentence,
                                                                    prev_word)
            if complete:
                break

        return sentence

    def add_next_word_to_sentence(self, sentence, word):
        sentence_is_complete = False

        if self.word_ends_sentence(word):
            sentence = "%s%s" % (sentence, word)
            sentence_is_complete = True
        elif self.word_has_no_space_before(word):
            sentence = "%s%s" % (sentence, word)
        else:
            sentence = "%s %s" % (sentence, word)

        return sentence, sentence_is_complete

    def add_previous_word_to_sentence(self, sentence, word):
        sentence_is_complete = False
        if self.word_ends_sentence(word):
            sentence_is_complete = True
        elif self.word_has_no_space_before(sentence[0]):
            sentence = "%s%s" % (word, sentence)
        else:
            sentence = "%s %s" % (word, sentence)

        return sentence, sentence_is_complete

    @staticmethod
    def word_has_no_space_before(word):
        no_space = [",", ";", ":"]
        return word in no_space

    @staticmethod
    def word_ends_sentence(word):
        ender = [".", "?", "!"]
        return word in ender

    def generate_stem(self, hint=None):
        """
        Returns a random couple of word from the database
        """
        if hint:
            stem = self.sql.find_tuple_containing_word(hint)
            if not stem:
                stem = self.sql.find_random_tuple()
        else:
            stem = self.sql.find_random_tuple()

        return stem

    def learn_from_sentence(self, sentence):
        """
        Extract words from a sentence and save them in the database.
        """
        sane_sentence = self.sanatize_sentence(sentence)
        words = sane_sentence.split()
        nb_of_words = len(words)
        if nb_of_words > 2:
            self.db_add_word_a(words[0], words[1], words[2])
            for i in range(nb_of_words - 3):
                self.db_add_word_ba(words[i],
                                    words[i+1],
                                    words[i+2],
                                    words[i+3])
            self.db_add_word_b(words[nb_of_words-3],
                               words[nb_of_words-2],
                               words[nb_of_words-1])

    @staticmethod
    def sanatize_sentence(sentence):
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
        return sentence

    def generate_image(self, image_url, font_name, hint=None):
        """
        Resize image and draw generated text on it, then return the result.
        """
        try:
            img = Image.open(BytesIO(urllib.request.urlopen(image_url).read()))
        except IOError as ex:
            raise ex

        resized_img = self.resize_image(img)
        stem = self.generate_stem(hint)
        sentence = self.generate_sentence(stem)
        text_block = textwrap.wrap(sentence, width=40)
        try:
            self.draw_text_block(resized_img, text_block, font_name)
        except Exception as ex:
            raise ex

        output = BytesIO()
        img.save(output, format='PNG')
        return output

    @staticmethod
    def resize_image(img):
        img_w, img_h = img.size
        ratio = max(600 / img_w, 600 / img_h)
        img_w *= ratio
        img_h *= ratio
        resized_img = img.resize((int(img_w), int(img_h)), Image.ANTIALIAS)

        return resized_img

    @staticmethod
    def draw_text_block(img, text_block, font_name):
        draw = ImageDraw.Draw(img)
        img_width, img_height = img.size
        font = ImageFont.truetype(font_name, 30)
        current_h = img_height / 10
        for line in text_block:
            text_width, text_height = draw.textsize(line, font=font)
            try:
                draw_text_with_border(draw,
                                      (img_width - text_width) / 2,
                                      current_h,
                                      (0, 0, 0, 255),
                                      (255, 255, 0, 255),
                                      line,
                                      font)
            except Exception as ex:
                raise ex
            current_h += text_height + 10

    def db_add_word_ba(self, prev_word, stem1, stem2, next_word):
        """
        Used when we have a sentence containing :
        "^ ... prev_word STEM1 STEM2 next_word ... $"
        """
        if word_is_okay(prev_word) \
        and word_is_okay(stem1) \
        and word_is_okay(stem2) \
        and word_is_okay(next_word):
            self.sql.add_previous_and_next_word(stem1,
                                                stem2,
                                                prev_word,
                                                next_word)

    def db_add_word_a(self, stem1, stem2, next_word):
        """
        Used when we have a sentence containing :
        "^STEM1 STEM2 next_word ... $"
        """
        if word_is_okay(stem1) \
        and word_is_okay(stem2) \
        and word_is_okay(next_word):
            self.sql.add_next_word(stem1, stem2, next_word)

    def db_add_word_b(self, stem1, stem2, prev_word):
        """
        Used when we have a sentence containing :
        "^ ... prev_word STEM1 STEM2$"
        """
        if word_is_okay(prev_word) \
        and word_is_okay(stem1) \
        and word_is_okay(stem2):
            self.sql.add_previous_word(stem1, stem2, prev_word)

    def db_count_base(self):
        """
        Returns the number of couples that are in 'base'
        """
        return self.sql.get_size_of_base()
