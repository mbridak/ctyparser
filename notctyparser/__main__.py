"""
ctyparser commandline interface
---

Copyright 2019-2022 classabbyamp, 0x5c
Released under the terms of the MIT license.
"""


# import argparse
import pathlib

import notctyparser

file = pathlib.PurePath("./cty.json")
try:
    cty = notctyparser.BigCty(file)
except FileNotFoundError:
    cty = notctyparser.BigCty()
print("Updated:", cty.update())
print("Datestamp:", cty.formatted_version)
print("Version Entity:", cty.get("VERSION", "Not present, data possibly corrupted."))
cty.dump(file)
