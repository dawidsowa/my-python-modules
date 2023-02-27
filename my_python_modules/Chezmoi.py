from configparser import ConfigParser
import json
from pathlib import Path
from sys import argv, stdin
import atexit
from io import StringIO
from subprocess import PIPE, run
from sys import argv
from yaml import safe_load, safe_dump
from bs4 import BeautifulSoup as bs
import yaml
import toml


WORKING_TREE = Path("~/.local/share/chezmoi/").expanduser()
SOURCE_DIR = WORKING_TREE / "home"

DATA_PATH = SOURCE_DIR / ".chezmoidata.json"
CONFIG_PATH = Path("~/.config/chezmoi/chezmoi.toml").expanduser()

DATA = json.load(DATA_PATH.open()) | toml.load(CONFIG_PATH.open())["data"]


class Chezmoi_INI(ConfigParser):
    def __init__(self):
        super().__init__()
        self.optionxform = str
        inp = ("").join(stdin.readlines())
        if inp == "":
            exit()
        self.read_string(inp)
        atexit.register(self.__write)

    def __write(self):
        with StringIO() as s:
            self.write(s, space_around_delimiters=False)
            s.seek(0)
            print(s.read())


def chezmoi_source(s):
    return run(
        ["chezmoi", "source-path", s], capture_output=True, text=True
    ).stdout.strip()


def chezmoi_translate(s):
    if isinstance(s, Path):
        s = str(s)

    for k, v in (
        {
            ".local/share/chezmoi/": "",
            "dot_": ".",
            "private_": "",
            "exact_": "",
            "executable_": "",
            "modify_": "",
        }
    ).items():
        s = s.replace(k, v)

    return s


def chezmoi_template(string):
    return run(["chezmoi", "execute-template", string], stdout=PIPE).stdout.decode(
        "utf-8"
    )


def yaml(file):
    return safe_dump(dict(file))


def comment_dict(file):
    options = ""

    with open(file) as f:
        while (x := next(f, None)) is not None and x.startswith("#"):
            if x[1] != "!":
                options += x[1:].lstrip()

    options = safe_load(options)
    if options is not None:
        options = {k.lower(): v for k, v in options.items()}
    else:
        options = {}

    return options


class Modify:
    def __init__(self, path=None, action=[], post=[]):
        self.text = Path(path).read_text()
        if callable(post):
            self.post_actions = [post]
        else:
            self.post_actions = post

        if callable(action):
            self.actions = [action]
        else:
            self.actions = action

    def __str__(self):
        return self.text

    def print(self):
        text = str(self)
        for x in self.post_actions:
            text = x(text)

        print(text)


class ModifyXML(Modify):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.soup = bs(self.text, features="xml")

    def act(self):
        for x in self.actions:
            self.soup = x(self.soup)

    def __str__(self):
        return self.soup.prettify()
