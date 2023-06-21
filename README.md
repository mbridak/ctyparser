# notctyparser

notctyparser is a fork and extension of [ctyparser](https://github.com/miaowware/ctyparser).

I've probably screwed something up. Use the original.

A CTY.DAT parser for modern amateur radio programs.

[![PyPI](https://img.shields.io/pypi/v/notctyparser)](https://pypi.org/project/notctyparser/) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/notctyparser) ![PyPI - License](https://img.shields.io/pypi/l/notctyparser)

## Installation

`notctyparser` requires Python 3.6 at minimum.

```none
pip install notctyparser
```

## Fork

I just added a stupid check for update without doing the update.

```python
def check_update(self) -> bool:
```

- Changed locale to en_US.utf8
- Used xpath to parse the download link.
- Chose more narrow raised exceptions.
- Specified utf-8 file encoding.
- Made the linter happy.

## Copyright

Copyright 2019-2022 classabbyamp, 0x5c  
Released under the MIT License.  
See `LICENSE` for the full license text.
