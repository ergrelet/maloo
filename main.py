# coding: utf8

"""
main.py
-------

Everything starts from here !
"""

import configparser
import sys

import ircbot

def main():
    """ Main function """
    print("Maloo Bot - In Python !\n")

    if len(sys.argv) < 2:
        sys.exit("Missing argument (config file) !")

    config = configparser.ConfigParser()
    config.read(sys.argv[1])
    bot = ircbot.IrcBot(config)
    bot.start()

if __name__ == "__main__":
    main()
