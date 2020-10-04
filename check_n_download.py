import requests
import pathlib
import pandas as pd
import time
import random
import argparse

import re

from bs4 import BeautifulSoup
from zipfile import ZipFile
from progress.bar import Bar

def _parse_mod_desc(file_name, soup: BeautifulSoup) -> pd.Series:
    return {"file_name": file_name,
            "mod_title": soup.find("title", recursive=True).en.contents[0].strip(),
            "author": soup.find("author", recursive=True).contents[0].strip(),
            "version": soup.find("version", recursive=True).contents[0],
            }


def check_local_mods(mod_path: pathlib.Path) -> pd.DataFrame:
    """
    gathers info about installed mods
    """
    installed_mods = pd.DataFrame()
    zip_files = list(mod_path.glob("*.zip"))
    for file_path in Bar("Indexing local mods").iter(zip_files):
        with ZipFile(file_path) as myzip:
            with myzip.open('modDesc.xml') as mod_desc:
                installed_mods = installed_mods.append(_parse_mod_desc(
                    file_path.name, BeautifulSoup(mod_desc.read(), "xml")), ignore_index=True)
    return installed_mods


ITEM_URL = "https://www.farming-simulator.com/mod.php?lang=en&country=se&mod_id={}&title=fs2019"
# VERSION_FILTER = '<div class="table-cell">1.0.0.0</div>'
# hmm, i no like soup.. is overkill
# we big thinks
VERSION_FILTER = '<div class="table-cell">{}</div>'
DOWNLOAD_RE = re.compile(
    r'<a href=\"(https:\/\/.*\.zip)\" class=\"button button-buy button-middle button-no-margin expanded\">DOWNLOAD<\/a>')


def check_mod_and_update(row, mod_dir,outer_bar,chunk_size=2**22):
    outer_bar.next()
    res = requests.get(ITEM_URL.format(row.mod_id)).text
    if res.find(VERSION_FILTER.format(row.version)) == -1:
        # not up to date... we asume that no user has mods that are newer than the modhub,
        # cause if you develop mods, you're probably not using this... but thank you for your service xD
        match = DOWNLOAD_RE.search(res)
        if match:
            dl_link = match.group(1)
            print(f'downloading update for mod {row.mod_title}')
            r = requests.get(dl_link, stream=True, headers={
                # kinda a lie, but hey it works..
                "referer": "https://giants-software.com/"
            })
            if r.ok:
                mod_path = (mod_dir / row.file_name)
                with mod_path.open("wb") as fd:
                    bar = Bar("Download",max = int(r.headers['content-length'])//chunk_size,suffix='%(percent)d%%')
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        fd.write(chunk)
                        bar.next()
                    bar.finish()
            else:
                print(
                    f"could not download update : {r.status_code} {r.reason}")
            return True
        else:
            print(f"could not find link for {row}")
            return False
    return None


def check_and_update(installed: pd.DataFrame, mod_path: pathlib.Path):
    bar = Bar("Checking local version",max=len(installed))
    results: pd.Series = installed.apply(
        lambda row: check_mod_and_update(row, mod_path,bar), axis=1)
    bar.finish()
    print(f'Installed updates for mods:')
    print(installed.loc[results == True])

    print(f'Failed to update mods:')
    print(installed.loc[results == False])
    print(f'Update these manually')
    return results
