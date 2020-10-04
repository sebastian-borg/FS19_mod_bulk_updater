import requests
import pathlib
import pandas as pd
import time
import random

from bs4 import BeautifulSoup
import bs4
import re

from progress.bar import Bar

PAGE_URL = "https://www.farming-simulator.com/mods.php?lang=en&country=se&title=fs2019&filter=latest&page={}"
MOD_ID_RE = re.compile(r'mod_id=(\d+)&')


def parse_page(soup: BeautifulSoup) -> pd.DataFrame:
    res = []
    items = soup.findAll(attrs={"class": "mod-item"})
    for item in items:
        if (match := MOD_ID_RE.search(item.find('a')['href'])):
            mod_id = match.group(1)
            content = item.find("div", attrs={"class": "mod-item__content"})
            entry = {"mod_title": content.h4.contents[0],
                     "author": content.p.span.contents[0].replace("By: ", "").strip(),
                     "mod_id": mod_id
                     }
        # else:
        # skipping dlc, giants plz make api.. or at least be consistent with the links
        res.append(entry)
    return pd.DataFrame(res)


def fetch_all_mod_info(random_sleep=False) -> pd.DataFrame:

    res = requests.get(PAGE_URL.format(0))
    soup = BeautifulSoup(res.content, "html.parser")

    pages: bs4.element.Tag = soup.find("ul", attrs={"role": "navigation"})
    max_page = int(next(pages.findChildren("a", recursive=True)[-1].children))
    bar:Bar = Bar("Indexing modHub",max=max_page)
    data: pd.DataFrame = parse_page(soup)
    bar.next()
    for i in range(1, max_page):
        if random_sleep:
            time.sleep(random.random())
        soup = BeautifulSoup(requests.get(
            PAGE_URL.format(i)).content, "html.parser")
        data = data.append(parse_page(soup))
        bar.next()
    data = data.drop_duplicates()
    bar.finish()
    return data
