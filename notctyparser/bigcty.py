"""
bigcty.py - part of miaowware/ctyparser
---

Copyright 2019-2022 classabbyamp, 0x5c
Released under the terms of the MIT license.
"""


import collections
import copy
import json
import locale
import os
import pathlib
import re
import tempfile
import zipfile
from datetime import datetime
from typing import Union

import feedparser
import requests
from lxml import html

DEFAULT_FEED = "http://www.country-files.com/category/big-cty/feed/"


class BigCty(collections.abc.Mapping):
    """Class representing a BigCTY dataset.
    Can be initialised with data by passing the path to a valid ``cty.json`` file
    to the constructor.

    :param file_path: Location of the ``cty.json`` file to load.
    :type file_path: str or os.PathLike, optional

    :var version: the datestamp of the data, ``YYYYMMDD`` format.
    :vartype version: str
    """

    regex_version_entry = re.compile(r"VER(\d{8})")
    regex_feed_date = re.compile(r"(\d{2}-\w+-\d{4})")
    regex_dat = re.compile(
        r"""=?(?P<prefix>[a-zA-Z0-9/]+)
                                 (?:\((?P<cq>\d+)\))?
                                 (?:\[(?P<itu>\d+)\])?
                                 (?P<latlong>
                                     <(?P<lat>[+-]?\d+(?:\.\d+)?)
                                     \/
                                     (?P<long>[+-]?\d+(?:.\d+)?)>
                                 )?
                                 (?:\{(?P<continent>\w+)\})?
                                 (?:~(?P<tz>[+-]?\d+(?:\.\d+)?)~)?""",
        re.X,
    )

    def __init__(self, file_path: Union[str, os.PathLike, None] = None):
        locale.setlocale(locale.LC_ALL, "en_US.utf8")
        self._data: dict = {}
        self._version = ""

        if file_path is not None:
            self.load(file_path)

    def load(self, cty_file: Union[str, os.PathLike]) -> None:
        """Loads a ``cty.json`` file into the instance.

        :param cty_file: Path to the file to load.
        :type cty_file: str or os.PathLike
        :return: None
        """
        cty_file = pathlib.Path(cty_file)
        with cty_file.open("r", encoding="utf-8") as file:
            ctyjson = json.load(file)
            self._version = ctyjson.pop("version", None)
            self._data = ctyjson

    def dump(self, cty_file: Union[str, os.PathLike]) -> None:
        """Dumps the data of the instance to a ``cty.json`` file.

        :param cty_file: Path to the file to dump to.
        :type cty_file: str or os.PathLike
        :return: None
        """
        cty_file = pathlib.Path(cty_file)
        datadump = self._data.copy()
        datadump["version"] = self._version
        with cty_file.open("w", encoding="utf-8") as file:
            json.dump(datadump, file)

    def import_dat(self, dat_file: Union[str, os.PathLike]) -> None:
        """Imports CTY data from a ``CTY.DAT`` file.

        :param dat_file: Path to the file to import.
        :type dat_file: str or os.PathLike
        :return: None
        """
        dat_file = pathlib.Path(dat_file)
        with dat_file.open("r", encoding="utf-8") as file:
            cty_dict = {}

            # get the version from the file
            ver_match = re.search(self.regex_version_entry, file.read())
            self._version = ver_match.group(1) if ver_match is not None else ""
            file.seek(0)

            # stores the previous prefix for the next iteration
            last = ""

            while True:
                line = (
                    file.readline().rstrip("\r").strip(":")
                )  # remove unnecessary carriage returns and colons
                if not line:
                    break
                # check if the line introduces new DXCC
                if line != "" and line[0].isalpha():
                    # split line into fields at delimiters
                    segments = [x.strip() for x in line.split(":")]
                    # check if this entity is not a DXCC
                    if segments[7][0] == "*":
                        segments[7] = segments[7][1:]
                        segments[0] += " (not DXCC)"
                    cty_dict[segments[7]] = {
                        "entity": segments[0],
                        "cq": int(segments[1]),
                        "itu": int(segments[2]),
                        "continent": segments[3],
                        "lat": float(segments[4]),
                        "long": float(segments[5]),
                        "tz": -1 * float(segments[6]),
                        "len": len(segments[7]),
                        "primary_pfx": segments[7],
                        "exact_match": False,
                    }
                    # store the current prefix for the next iteration
                    last = segments[7]

                # check if the line continues a DXCC
                elif line != "" and line[0].isspace():
                    overrides = line.strip().rstrip(";").rstrip(",").split(",")

                    for item in overrides:
                        if item not in cty_dict:
                            # get the already stored data from primary prefix
                            data = copy.deepcopy(cty_dict[last])
                            # apply regex to extract the prefix and overrides
                            match = re.search(self.regex_dat, item)
                            if match is None:
                                continue
                            if match.group("itu"):
                                data["itu"] = int(match.group("itu"))
                            if match.group("cq"):
                                data["cq"] = int(match.group("cq"))
                            if match.group("latlong"):
                                data["lat"] = float(match.group("lat"))
                                data["long"] = float(match.group("long"))
                            if match.group("continent"):
                                data["continent"] = match.group("continent")
                            if match.group("tz"):
                                data["tz"] = -1 * float(match.group("tz"))
                            if item.startswith("="):
                                data["exact_match"] = True
                            prefix = match.group("prefix")
                            cty_dict[prefix] = data
        self._data = cty_dict

    def check_update(self) -> bool:
        """Checks if an update exists.
        :raises AttributeError : If there is no date in the feed.
        :return: ``True`` if an update is available, otherwise ``False``.
        :rtype: bool
        """
        with requests.Session() as session:
            feed = session.get(DEFAULT_FEED)
            parsed_feed = feedparser.parse(feed.content)
            update_url = parsed_feed.entries[0]["link"]
            date_match = re.search(self.regex_feed_date, update_url)
            if date_match is None:
                raise AttributeError("Error parsing feed: date missing")
            date_str = date_match.group(1).title()
            update_date = datetime.strftime(
                datetime.strptime(date_str, "%d-%B-%Y"), "%Y%m%d"
            )

            if self._version == update_date:
                return False
            return True

    def update(self) -> bool:
        """Upates the instance's data from the feed.

        :raises AttributeError: If there is no date in the feed.
        :raises ResourceWarning: If unable to download bigcty.
        :return: ``True`` if an update was done, otherwise ``False``.
        :rtype: bool
        """
        with requests.Session() as session:
            feed = session.get(DEFAULT_FEED)
            parsed_feed = feedparser.parse(feed.content)
            update_url = parsed_feed.entries[0]["link"]
            date_match = re.search(self.regex_feed_date, update_url)
            if date_match is None:
                raise AttributeError("Error parsing feed: date missing")
            date_str = date_match.group(1).title()
            update_date = datetime.strftime(
                datetime.strptime(date_str, "%d-%B-%Y"), "%Y%m%d"
            )

            if self._version == update_date:
                return False

            with tempfile.TemporaryDirectory() as temp:
                path = pathlib.PurePath(temp)
                page = session.get(update_url)
                tree = html.fromstring(page.content)
                urls = tree.xpath("//a[contains(@href,'zip')]/@href")
                if len(urls) == 0:
                    raise ResourceWarning(
                        f"Unable to find and download bigcty-{update_date}.zip"
                    )
                dl_url = urls[0]
                the_request = session.get(dl_url)
                if the_request.status_code == 404:
                    dl_url = (
                        "http://www.country-files.com/bigcty/download/bigcty-"
                        f"{update_date}.zip"
                    )
                    the_request = session.get(dl_url)
                    if the_request.status_code != 200:
                        raise ResourceWarning(
                            f"Unable to find and download bigcty-{update_date}.zip"
                        )
                with open(path / "cty.zip", "wb+") as file:
                    file.write(the_request.content)
                    zipfile.ZipFile(file).extract(
                        "cty.dat", path=str(path)
                    )  # Force cast as str because mypy
                self.import_dat(path / "cty.dat")
        return True

    @property
    def formatted_version(self) -> str:
        """Formatted representation of the version/date of the current BigCTY data.

        :getter: Returns version in ``YYYY-MM-DD`` format, or ``0000-00-00`` (if invalid date)
        :type: str
        """
        try:
            return datetime.strptime(self._version, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return "0000-00-00"

    @property
    def version(self) -> str:
        """The version/date of the current BigCTY data.

        :getter: Returns version in ``YYYYMMDD`` format
        :type: str
        """
        return self._version

    # --- Wrappers to implement dict-like functionality ---
    def __len__(self):
        return len(self._data)

    def __getitem__(self, key: str):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    # --- Standard methods we should all implement ---
    # str(): Simply return what it would be for the underlaying dict
    def __str__(self):
        return str(self._data)

    # repr(): Class name, instance ID, and last_updated
    def __repr__(self):
        return (
            f"<{type(self).__module__}.{type(self).__qualname__} object"
            f"at {hex(id(self))}, last_updated={self.last_updated}>"
        )
