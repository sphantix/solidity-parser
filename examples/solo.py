#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Author: Sphantix
# Mail: sphantix@gmail.cn
# created time: Wed 13 Jun 2018 03:14:24 PM CST

import sys
import json
from solidity_parser import Trim, SolidityParser

def print_usage():
    print("""Usage:
            $./solo.py <file>
            $python3 solo.py <file>""")

def main():
    EF = "$"

    if len(sys.argv) != 2:
        print_usage()
        return

    file = sys.argv[1]

    # parse file
    with open(file, 'r') as f:
        content = f.read()
        # trim file content
        content = Trim.strip_comments(content)
        content = Trim.strip_spaces(content)
        content = content + ' ' + EF
        print(content)
        # parse file
        parser = SolidityParser(content, EF)
        result = parser.parse()
        print(json.dumps(result, indent=4))


if __name__ == "__main__":
    main()
