# coding: utf8

"""
maloosql.py
--------

Here's the definition of the MalooSql class.
"""

from random import randrange
import sqlite3

class MalooSql(object):

    def __init__(self, sql_config):
        self.sqldb = sqlite3.connect(sql_config["db_name"])

    def find_tuple_containing_word(self, word):
        sqlcursor = self.sqldb.cursor()
        word_doublequoted = word.replace("'", "''")
        query = """SELECT word1, word2
                FROM base
                WHERE (lower(word1)=lower('{0}') or lower(word2)=lower('{0}'))
                ORDER BY RANDOM()
                LIMIT 1""".format(word_doublequoted)
        sqlcursor.execute(query)
        rows = sqlcursor.fetchall()

        result_is_empty = (len(rows) == 0)
        if result_is_empty:
            stem = None
        else:
            [word, next_word] = rows[0]
            stem = (word, next_word)

        return stem

    def find_random_tuple(self):
        sqlcursor = self.sqldb.cursor()
        query = """SELECT word1, word2
                FROM base
                ORDER BY RANDOM()
                LIMIT 1"""
        sqlcursor.execute(query)
        rows = sqlcursor.fetchall()

        result_is_empty = (len(rows) == 0)
        if result_is_empty:
            stem = None
        else:
            stem = (rows[0][0], rows[0][1])

        return stem

    def find_next_word(self, word1, word2):
        sqlcursor = self.sqldb.cursor()
        word1_doublequoted = word1.replace("'", "''")
        word2_doublequoted = word2.replace("'", "''")
        sqlcursor.execute("""SELECT next.word
                            FROM base
                            INNER JOIN next
                            ON base.id = next.stem_id
                            WHERE lower('{}') = lower(base.word1)
                            AND lower('{}') = lower(base.word2)
                            ORDER BY probability DESC
                            LIMIT 15""".format(word1_doublequoted,
                                               word2_doublequoted))
        rows = sqlcursor.fetchall()
        nb_of_results = len(rows)
        if nb_of_results == 0:
            next_word = None
        else:
            next_id = randrange(0, nb_of_results)
            next_word = rows[next_id][0].lower()
        return next_word

    def find_previous_word(self, word1, word2):
        sqlcursor = self.sqldb.cursor()
        word1_doublequoted = word1.replace("'", "''")
        word2_doublequoted = word2.replace("'", "''")
        sqlcursor.execute("""SELECT previous.word
                            FROM base
                            INNER JOIN previous
                            ON base.id = previous.stem_id
                            WHERE lower('{}') = lower(base.word1)
                            AND lower('{}') = lower(base.word2)
                            ORDER BY probability DESC
                            LIMIT 15""".format(word1_doublequoted,
                                               word2_doublequoted))
        rows = sqlcursor.fetchall()
        nb_of_results = len(rows)
        if nb_of_results == 0:
            previous_word = None
        else:
            previous_id = randrange(0, nb_of_results)
            previous_word = rows[previous_id][0].lower()
        return previous_word

    def add_previous_and_next_word(self, word1, word2, previous_word, next_word):
        self.add_previous_word(word1, word2, previous_word)
        self.add_next_word(word1, word2, next_word)

    def add_next_word(self, word1, word2, next_word):
        sqlcursor = self.sqldb.cursor()
        sqlcursor.execute("""INSERT OR IGNORE INTO base
                          VALUES (null, '{}', '{}')""".format(word1, word2))
        sqlcursor.execute("""SELECT id
                          FROM base
                          WHERE word1 = '{}'
                          AND word2 = '{}'""".format(word1, word2))
        rows = sqlcursor.fetchall()
        stem_id = rows[0][0]
        sqlcursor.execute("""INSERT OR IGNORE INTO next
                          VALUES ({}, '{}', 1)""".format(stem_id, next_word))
        sqlcursor.execute("""UPDATE next SET probability = probability + 5
                          WHERE stem_id LIKE {}""".format(stem_id))
        self.sqldb.commit()

    def add_previous_word(self, word1, word2, prev_word):
        sqlcursor = self.sqldb.cursor()
        sqlcursor.execute("""INSERT OR IGNORE INTO base
                                    VALUES (null, '{}', '{}')""".format(word1,
                                                                        word2))
        sqlcursor.execute("""SELECT id
                          FROM base
                          WHERE word1 = '{}'
                          AND word2 = '{}'""".format(word1, word2))
        rows = sqlcursor.fetchall()
        stem_id = rows[0][0]
        sqlcursor.execute("""INSERT OR IGNORE INTO previous
                          VALUES ({}, '{}', 1)""".format(stem_id, prev_word))
        sqlcursor.execute("""UPDATE previous SET probability = probability + 5
                          WHERE stem_id LIKE {}""".format(stem_id))
        self.sqldb.commit()

    def get_size_of_base(self):
        sqlcursor = self.sqldb.cursor()

        sqlcursor.execute("SELECT COUNT(*) FROM base")
        (result,) = sqlcursor.fetchone()

        return result
