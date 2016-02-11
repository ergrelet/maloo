# coding: utf8

from random import randrange
import socket

import maloobot

class IrcBot:
	def __init__(self, config):
		config_irc = config["irc"]
		config_sql = config["sql"]
		config_api = config["api"]
		
		self.server = config_irc["server"]
		self.port = config_irc["port"]
		self.nick = config_irc["nick"]
		self.username = config_irc["username"]
		self.realname = config_irc["realname"]
		self.password = config_irc["password"]
		self.channels = config_irc["channels"].strip().split(",")
		self.admins = config_irc["admins"].strip().split(",")
		self.now_learning = True
		
		self.maloo = maloobot.MalooBot(config_sql, config_api)	
		
	def on_ping(self, server):
		print("Ping received from {}, sending Pong !".format(server))
		self.socket.send(bytes("PONG :{}\r\n".format(server), 'UTF-8'))
	
	def on_join(self, channel):
		print("Joined " + channel)
	
	def on_quit(self):
		self.socket.close()
	
	def on_privmsg(self, user, channel, message):
		if user == self.nick:
			return

		words = message.split(" ")
		nb_of_words = len(words)
		if words[0] == "!quit" and user in self.admins:
			print(user + " ordered me to quit, bye !")
			self.disconnect("Je vous en prie.")
		elif words[0] == "!maloo_text":
			self.privmsg(channel, self.maloo.generate_sentence())
		elif words[0] == "!maloo_image":
			if nb_of_words > 1:
				hint = words[1]
			else:
				hint = ""
			self.privmsg(channel, self.maloo.generate_image(hint))
		elif words[0] == "!learn" and user in self.admins:
			if self.now_learning:
				self.privmsg(channel, "Argh, la flemme s'empare de moi ...")
				self.now_learning = False
			else:
				self.privmsg(channel, "J'écoute !")
				self.now_learning = True
		elif words[0] == "!count":
			self.privmsg(channel, "Je connais {} couples de mots".format(self.maloo.db_count_base()))
		elif words[0] == "!help":
			self.privmsg(channel, "List of available commands :")
			self.privmsg(channel, "!maloo_image - Generate an image with some awesome text on it.")
			self.privmsg(channel, "!maloo_text - Generate a perfectly written sentence and sends it in this channel.")
			self.privmsg(channel, "!count - Display the number of couple of words currently present in the database.")
			self.privmsg(channel, "!learn - Teach me your ways, Sensei (ADMIN ONLY)")
			self.privmsg(channel, "!quit - Pls no. (ADMIN ONLY)")
		elif message.find(self.nick) > -1:
			message = message.replace(self.nick, "")
			self.privmsg(channel, "{}: {}".format(pseudo, self.maloo.generate_answer(message)))
		elif self.now_learning and nb_of_words > 3 and message[0] != "!":
			self.maloo.learnfrom_sentence(message)
	
	def connect(self, server, port):
			print("Connecting to {}:{}".format(self.server, self.port))
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			try:
				self.socket.connect((self.server, int(self.port)))
			except Exception:
				raise Exception
	
	def disconnect(self, message = "Leaving"):
			self.socket.send(bytes("QUIT :{}\r\n".format(message), 'UTF-8'))
			self.socket.close()

	def privmsg(self, channel, message):
		self.socket.send(bytes("PRIVMSG {} :{}\r\n".format(channel, message), 'UTF-8'))
		
	def join(self, channel):
		self.socket.send(bytes("JOIN {}\r\n".format(channel), 'UTF-8'))
		
	def setnick(self, nickname):
		self.socket.send(bytes("NICK {}\r\n".format(nickname), 'UTF-8'))
		
	def setuser(self, username, realname):
		self.socket.send(bytes("USER {0} {0} {0} :{1}\r\n".format(username, realname), 'UTF-8'))
		
	def start(self):
		try:
			self.connect(self.server, int(self.port))
		except Exception:
			print("Can't connect to the server !")
			return

		self.setnick(self.nick)
		self.setuser(self.username, self.realname)

		# Joining channels
		for channel in self.channels:
			self.join(channel)

		# Main loop
		while True:
			data = self.socket.recv(256)
			try:
				sdata = data.decode("utf-8")
			except UnicodeDecodeError:
				print("Error while decoding, skipping packet")
				continue
			fields = sdata.split(':', 2)
			nb_of_fields = len(fields)
			if nb_of_fields > 1:
				cmd_args = fields[1].split(' ')
				nb_of_args = len(cmd_args)
				if nb_of_args > 1:
					if cmd_args[1] == "PRIVMSG":
						username = fields[1].split('!', 1)[0]
						message = fields[2].replace("\r", "").replace("\n", "")
						self.on_privmsg(username, cmd_args[2], message)
					elif cmd_args[1] == "JOIN":
						self.on_join(cmd_args[2])
					elif cmd_args[1] == "QUIT":
						self.on_quit()
				if fields[0].strip() == "PING":
					server = fields[1].replace("\r", "").replace("\n", "")
					self.on_ping(server)

		self.disconnect("Chelou.")
		print("Disconnected !")