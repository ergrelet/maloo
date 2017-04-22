#!/usr/bin/env python
# coding: utf8

"""
main.py
-------

Everything starts from here !
"""

import sys
import configparser

import malooirc

def main(argc, argv):
    """
    Main function
    """
    if argc < 2:
        sys.exit("Usage: %s [config file]" % argv[0])

    print("Maloo ready for duty !\n")
    config = configparser.ConfigParser()
    config.read(argv[1])
    bot = malooirc.MalooIrc(config)
    bot.start()

if __name__ == "__main__":
    main(len(sys.argv), sys.argv)
    sys.exit(1)
