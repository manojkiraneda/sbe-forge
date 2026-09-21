#!/usr/bin/env python3
"""Remove LLVM 22 memory attributes before feeding IR to LLVM 21."""

import re
import sys


source, destination = sys.argv[1:]
with open(source, encoding='utf-8') as input_file:
    ir = input_file.read()

with open(destination, 'w', encoding='utf-8') as output_file:
    output_file.write(re.sub(r'memory\([^)]*\) *', '', ir))
