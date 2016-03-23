# coding: utf8

"""
malooirc.py
--------

Here's the definition of the MalooIrc class.
"""

import irc.bot
import irc.client

import malooapi
import maloomarkov

class MalooIrc(irc.bot.SingleServerIRCBot):
    """
    This is simple class that is able to connect to the an irc server,
    set a nick / username / realname, join a list of channels
    and that embeds a MalooMarkov object in order to communicate in the chat.
    """
    def __init__(self, config):
        config_irc = config["irc"]
        irc.client.ServerConnection.buffer_class.errors = 'replace'
        irc.bot.SingleServerIRCBot.__init__(
            self,
            [(config_irc["server"], int(config_irc["port"]))],
            config_irc["nick"],
            config_irc["realname"]
        )

        self.ch_list = config_irc["channels"].strip().split(",")
        self.blacklist = config_irc["blacklist"].strip().split(",")
        self.admins = config_irc["admins"].strip().split(",")
        self.now_learning = True

        self.maloo = maloomarkov.MalooMarkov(config["sql"])
        self.api = malooapi.MalooApi(config["api"])
    
    def on_welcome(self, server, e):
        """ Connected to the server """
        for channel in self.ch_list:
            server.join(channel)

    def on_pubmsg(self, server, e):
        """ Received a message from a channel """
        user = e.source.nick
        message = e.arguments[0]
        channel = e.target
        my_nickname = server.get_nickname()
        
        if user == my_nickname or user in self.blacklist:
            return

        words = message.split(" ")
        nb_of_words = len(words)

        if words[0] == "!quit" and user in self.admins:
            print(user + " ordered me to quit, bye !")
            self.die(msg="Je vous en prie.")

        elif words[0] == "!text":
            if nb_of_words > 1:
                query = message.replace(words[0], "")
                server.privmsg(channel, self.maloo.generate_answer(query))
            else:
                server.privmsg(channel, self.maloo.generate_sentence())

        elif words[0] == "!image":
            if nb_of_words > 1:
                hint = words[1]
                query = message.replace(words[0], "")
            else:
                hint = ""
                query = " ".join(self.maloo.generate_stem())

            # Google
            try:
                image_url = self.api.find_on_googleimage(query)
            except Exception:
                server.privmsg(channel, "Google répond pas ...")
                return

            # Maloo
            try:
                image = self.maloo.generate_image(image_url, "./fonts/coolvetica.ttf", hint)
            except Exception:
                server.privmsg(channel, "Imprimante bloquée, bourrage papier ...")
                return

            # Imgur
            try:
                imgur_url = self.api.upload_to_imgur(image)
            except Exception:
                server.privmsg(channel, "Imgur ne me répond pas :(")
                return
            # Twitter
            self.api.post_on_tweet("Image generated by {} : {}".format(user, imgur_url))
            # IRC
            server.privmsg(channel, imgur_url)

        elif words[0] == "!learn" and user in self.admins:
            if self.now_learning:
                server.privmsg(channel, "Argh, la flemme s'empare de moi ...")
                self.now_learning = False
            else:
                server.privmsg(channel, "J'écoute !")

        elif words[0] == "!count":
            server.privmsg(channel, """Je connais {} couples de mots
                                         """.format(self.maloo.db_count_base()))
        elif words[0] == "!help":
            server.privmsg(channel, "List of available commands :")
            server.privmsg(channel, """!image -
                                             Generate an image with some awesome text on it.""")
            server.privmsg(channel, """!text -
                                             Generate a perfectly written sentence
                                            and sends it in this channel.""")
            server.privmsg(channel, """!count -
                                             Display the number of couple of words
                                            currently present in the database.""")
            server.privmsg(channel, "!learn - Teach me your ways, Sensei (ADMIN ONLY)")
            server.privmsg(channel, "!quit - Pls no. (ADMIN ONLY)")

        elif message.find(my_nickname) > -1:
            message = message.replace(my_nickname, "")
            server.privmsg(channel, "{}: {}".format(user, self.maloo.generate_answer(message)))

        elif self.now_learning and nb_of_words > 3 and message[0].isalpha():
            self.maloo.learnfrom_sentence(message)
