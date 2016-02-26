# coding: utf8

"""
main.py
-------

Everything starts from here !
"""

import configparser
import sys

import malooirc

def main():
    """ Main function """
    print("Maloo's back, in Python !\n")
    print("Let's do this shit ...")

    if len(sys.argv) < 2:
        sys.exit("Missing argument (config file) !")

    config = configparser.ConfigParser()
    config.read(sys.argv[1])
    bot = malooirc.MalooIrc(config)
    bot.start()

if __name__ == "__main__":
    main()
