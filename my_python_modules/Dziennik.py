#!/usr/bin/env python3
import base64
from hashlib import sha1
from logging import info
import os
import re
from importlib import resources
from pathlib import Path


from subprocess import run, PIPE
from datetime import datetime
from urllib.parse import urlparse, parse_qs, ParseResult, urljoin
from urllib.request import Request
from shutil import copy
from bs4 import BeautifulSoup, element


from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from PIL import Image

from selenium.webdriver.common.by import By
import io
from urllib.request import urlopen
from Moje.Shell import gallery_dl, XDG_DOCUMENTS_DIR, XDG_DOWNLOAD_DIR
from Moje.Chezmoi import DATA

import locale
import os
import holidays
from datetime import timedelta, datetime

from pathlib import Path


USER_AGENT = "Mozilla/5.0 (Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"


# TODO replace

DIARY = Path(DATA["diary"])
CONFIG = Path.home() / ("AppData/Roaming" if os.name == "nt" else ".config")


class AlreadyInsertedError(Exception):
    pass


def Get_Page(url):
    if isinstance(url, ParseResult):
        url = url.geturl()
    req = Request(url, headers={"User-Agent": USER_AGENT})
    return BeautifulSoup(urlopen(req), features="lxml")


def Get_Title(url):
    return Get_Page(url).title.string.replace("\n", " ").strip()


def setup_selenium(url):
    if isinstance(url, ParseResult):
        url = url.geturl()

    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    driver.get(url)

    return driver


class Content:
    @staticmethod
    def identify(inp):
        if isinstance(inp, Image.Image):
            return inp

        url = urlparse(str(inp))
        if url.scheme == "https" or url.scheme == "http":
            return url
        elif url.scheme == "":
            p = Path(inp)
            if p.exists():
                return p

    def __new__(cls, raw_input, *rest, **kwargs):

        match cls.identify(raw_input):
            case ParseResult(netloc="www.youtube.com"):
                cls = Youtube
            case ParseResult(netloc="archiveofourown.org"):
                cls = AO3
            case ParseResult(netloc="xkcd.com"):
                cls = XKCD
            case ParseResult(netloc="www.deconreconstruction.com"):
                cls = VE
            case ParseResult(netloc="www.girlgeniusonline.com"):
                cls = GG
            case ParseResult(netloc="www.smbc-comics.com"):
                cls = SMBC
            case ParseResult(netloc="www.prequeladventure.com"):
                cls = PrequelBooru
            case ParseResult(netloc="knowyourmeme.com", path=path) if path.startswith(
                "/photos/"
            ):
                cls = KYM
            case ParseResult(netloc="mspfa.com"):
                cls = MSPFA
            case ParseResult():
                cls = GDL
            case Path(suffix=(".gif" | ".png" | ".jpg" | ".webp" | ".svg")):
                cls = ImageFile
            case _:
                raise NotImplementedError

        return object.__new__(cls)

    def __str__(self):
        return self.markdown()

    def __init__(self, input, dir=XDG_DOWNLOAD_DIR, entry=None):
        self.link = None
        self.img = None
        self.description = None
        self.preprocessed = False
        self.io_run = False
        self.basename = self.__class__.__name__.lower()
        self.stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.entry = entry
        self.dir = Path(dir) if self.entry is None else entry.parents[0]

        self.input = input
        self.parsed = self.identify(self.input)

        self.handle()
        self.preprocess()

    def io_phase(self):
        pass

    def markdown_phase(self):
        pass

    def check_id(self):
        return None

    def check_phase(self):
        if self.entry is not None and self.check_id is not None:
            if self.entry.contains_string(self.check_id()):
                raise AlreadyInsertedError

    def markdown(self):
        self.check_phase()

        if not self.io_run:
            info("IO Phase")
            self.io_phase()
            self.io_run = True

        return self.markdown_phase()

    def download_image(self, url):
        hash = base64.urlsafe_b64encode(
            sha1(self.link.encode("utf-8")).digest()
        ).decode("utf-8")
        bname = f"{self.basename}{hash}"
        target = self.dir / bname
        run(["wget", url, "-O", target, "--restrict-file-names=nocontrol"])
        return bname

    # # TODO: Split into markdown and io_phase
    # @notify_exception
    # def markdown_phase(self):
    #     match self.img:
    #         case Image.Image():
    #             img = f"{self.basename}_{self.stamp}.png"
    #             path = self.dir / img
    #             self.img.save(path)
    #         case _:
    #             img = self.img

    #     if self.img is not None and self.link is not None:
    #         format_string = self.LINK_IMAGE
    #     elif self.img is not None:
    #         format_string = self.IMAGE

    def preprocess(self):
        if self.description is not None:
            assert isinstance(self.description, str)
            self.description = self.description.replace("\n", " ")

        if isinstance(self.link, ParseResult):
            self.link = self.link.geturl()


class Link(Content):
    def markdown_phase(self):
        return f"[{self.description}]({self.link})"


class ImageBase(Content):
    def check_id(self):
        return self.img

    def _single_markdown_image(self, description=None, link=None, img=None):
        description = description if description is not None else self.description
        link = link if link is not None else self.link
        img = img if img is not None else self.img

        if description and link:
            description = " - ".join([description, link])
        elif link:
            description = link
        elif not description:
            description = ""

        return f"![{description}]({img})"

    def markdown_phase(self):
        return "\n".join(
            [
                self._single_markdown_image(description="", link="", img=x)
                for x in self.img[:-1]
            ]
            + [self._single_markdown_image(img=self.img[-1])]
        )


class ImageFile(ImageBase):
    target = None

    def handle(self):
        file = self.parsed

        self.img = file.name
        self.description = file.name

    def io_phase(self):
        self.target = self.dir / self.img

        if not self.target.is_file():
            copy(self.parsed, self.target)
        elif self.target == self.img:
            pass
        else:
            raise FileExistsError(self.target)


class MSPFA(Content):
    def handle(self):
        q = parse_qs(self.parsed.query)
        self.stamp = f"{q['s'][0]}_{q['p'][0]}"
        driver = setup_selenium(self.input)
        self.img = driver.find_element(By.ID, "slide")
        self.img = Image.open(io.BytesIO(self.img.screenshot_as_png))
        self.description = driver.find_element(By.ID, "command")
        self.description = self.description.get_attribute("innerText")
        driver.close()


class GDL(ImageBase):
    def check_id(self):
        return self.img[-1]

    def handle(self):
        out = [
            x.split("\x1d")
            for x in gallery_dl(
                self.input, Path(self.dir) / "media", "diary.json"
            ).split("\x1c")
            if x != "" and x != "\n"
        ]
        # extractor = out[0][0]

        self.link = out[0][2]
        self.description = out[0][3]
        self.img = [x[1] for x in out]


class ImageBySelector(ImageBase):
    img_selector = None
    title_selector = None

    def handle(self):
        page = Get_Page(self.input)

        self.img = page.select_one(self.img_selector)
        if self.title_selector is not None:
            self.description = page.select_one(self.title_selector).text.strip()

        self.link = self.input

    def preprocess(self):
        try:
            self.img = urljoin(self.input, self.img.attrs["src"])
        except KeyError:
            self.img = urljoin(self.input, self.img.attrs["href"])

        super().preprocess()

    def io_phase(self):
        self.img = self.download_image(self.img)


class XKCD(ImageBySelector):
    img_selector = "div#comic img"
    title_selector = "div#ctitle"


class PrequelBooru(ImageBySelector):
    img_selector = "#main_image"


class SMBC(ImageBySelector):
    img_selector = "img#cc-comic"

    def handle(self):
        super().handle()
        self.description = self.img["title"]


class GG(ImageBySelector):
    img_selector = '#comicbody img[alt="Comic"]'


class KYM(ImageBySelector):
    img_selector = "#photo_wrapper a.magnify"
    title_selector = "#media-title"


class AO3(Link):
    def handle(self):
        input = self.parsed._replace(
            path=self.parsed.path.split("/chapters/")[0], fragment=""
        ).geturl()
        title = Get_Title(input)
        m = re.match("(.*) - Chapter .* - (.*) - .*", title)
        if m is None:
            m = re.match("(.*) - (.*) - .*", title)
        self.description = f"{m.group(1)} - {m.group(2)}"
        self.link = input


class VE(ImageBySelector):
    img_selector = "#content img"
    title_selector = "#command"


class Youtube(Content):
    def handle(self):
        id = parse_qs(self.parsed.query)["v"][0].strip()
        self.description = Get_Title(self.input)
        self.img = f"https://img.youtube.com/vi/{id}/0.jpg"
        self.link = f"https://www.youtube.com/embed/{id}"

    def markdown_phase(self):
        return f'<iframe src="{self.link}" title="{self.description}"></iframe>'


class Entry(type(Path())):
    def __new__(cls, **kwargs):
        date = kwargs.get("date", datetime.now())
        path = DIARY / (date + timedelta(hours=-4)).strftime("%Y/%m/%d.md")
        return super().__new__(cls, path, **kwargs)

    def __init__(self, **kwargs):
        locale.setlocale(locale.LC_TIME, "pl_PL")

        self.date = datetime.now()
        self.entry_date = kwargs.get("date", self.date)
        create = kwargs.get("create", True)
        insert_time = kwargs.get("insert_time", True)

        if not self.exists() and create:
            #  To ensure that if DIARY does not exist, it is not created.
            month, year, *_ = self.parents
            year.mkdir(exist_ok=True)
            month.mkdir(exist_ok=True)

            with self.open("w") as f:
                holiday = holidays.PL().get(self.entry_date)

                f.write(self.entry_date.strftime("# %d %A"))
                if holiday is not None:
                    f.write(" - ")
                    f.write(holiday)
                f.write("\n\n")

                p = DIARY
                past_entries = p.glob(self.entry_date.strftime("*/%m/%d.md"))
                for entry in list(past_entries)[0:-1]:
                    f.write(
                        f"[Wpis z {str(entry.relative_to(DIARY))}](../../{str(entry.relative_to(DIARY))})\n"
                    )

        if insert_time:
            self.insert_time()

    def contains_string(self, string):
        return str(string) in self.read_text()

    def append(self, *args):

        if args:
            with self.open("a") as f:
                f.writelines([f"{x}\n" for x in ["", "", *args]])

    def download_url(self, url):
        try:
            c = Content(url, entry=self)
            self.append(str(c))
        except AlreadyInsertedError:
            pass
        except FileExistsError as e:
            print(e)

    def insert_time(self):
        format = (
            "%H:%M" if self.date.date() == self.entry_date.date() else "%d %a - %H:%M"
        )
        self.append(f"## {self.date.strftime(format)}")


def get_entry(date=datetime.now(), offset=0, insert_time=True):  # legacy
    return Entry(date=date, offset=offset, insert_time=insert_time)
