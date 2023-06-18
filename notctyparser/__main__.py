"""
ctyparser commandline interface
---

Copyright 2019-2022 classabbyamp, 0x5c
Released under the terms of the MIT license.
"""


import os
import pathlib

import notctyparser

file = pathlib.PurePath("./cty.json")
try:
    cty = notctyparser.BigCty(file)
except FileNotFoundError:
    cty = notctyparser.BigCty()

print(f"LANG: {os.environ.get('LANG')}")
print(f"LC_TIME: {os.environ.get('LC_TIME')}")
print("Update:", cty.check_update())
print("Updated:", cty.update())
print("Datestamp:", cty.formatted_version)
print("Version Entity:", cty.get("VERSION", "Not present, data possibly corrupted."))
cty.dump(file)
