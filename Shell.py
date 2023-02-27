from json import loads
import os
from pathlib import Path
from subprocess import PIPE, CalledProcessError, run
from urllib.parse import urlparse

from io import BytesIO
from subprocess import PIPE, run

from PIL import ImageGrab, Image

from pyperclip import paste

import psutil


def cmd(args):
    return run(args, capture_output=True, text=True).stdout.strip()


def checkIfProcessRunning(processName):
    """
    Check if there is any running process that contains the given name processName.
    """
    # Iterate over the all the running process
    for proc in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if processName.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


if os.name != "nt":
    XDG_DOCUMENTS_DIR = Path(cmd(["xdg-user-dir", "DOCUMENTS"]))
    XDG_DOWNLOAD_DIR = Path(cmd(["xdg-user-dir", "DOWNLOAD"]))
    XDG_MUSIC_DIR = Path(cmd(["xdg-user-dir", "MUSIC"]))
    XDG_PICTURES_DIR = Path(cmd(["xdg-user-dir", "PICTURES"]))


def gnome_screenshot(mode):
    run(["gnome-screenshot", f"--{mode}"])


def notify_send(title, body="", icon=None):
    args = ["notify-send", "--hint=int:transient:1", title, body]
    if icon is not None:
        args = args + ["--icon", icon]
    run(args)


def notify_exception(func):
    def wrapped(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            notify_send(type(e).__name__, str(e))
            raise e

    return wrapped


class NoExtractorError(RuntimeError):
    def __init__(self, message):

        message = f"No suitable extractor found for:\n'{message}'"

        super().__init__(message)


@notify_exception
def gallery_dl(url, dest=None, config=None, range=None, args=[]):
    parsed = urlparse(url)

    if not parsed.scheme:
        raise ValueError("Not an URL")

    if "nitter" in parsed.netloc:
        url = parsed._replace(netloc="twitter.com").geturl()

    if dest is not None:
        args += ["--directory", Path(dest)]

    if config is not None:
        config = Path(config)

        if not config.is_absolute():
            config = Path("~/.config/gallery-dl") / config

        args += ["--config", config]

    if range is not None:
        args += ["--range", range]

    try:
        return run(["gallery-dl", url] + args, stdout=PIPE, check=True).stdout.decode(
            "utf-8"
        )
    except CalledProcessError as err:
        if err.returncode == 64:
            raise NoExtractorError(url)
        else:
            raise err


def gallery_dl_support(domain):
    notify_send(domain)

    return any(x in domain for x in ["deviantart.com", "nitter"])


def ydotool_key(keys):
    run(
        ["ydotool", "key"]
        + [str(k) + ":1" for k in keys]
        + [str(k) + ":0" for k in keys]
    )


# Ctrl = 29
# Shift = 42
# S = 31
# Print = 210


class Clipboard:
    def grab(self):
        if "text/plain" in self.targets():
            return self.paste("text/plain").decode("utf-8")

    def grab_image(self):
        if "image/png" in self.targets():
            stream = BytesIO(self.paste("image/png"))
            image = Image.open(stream).convert("RGBA")
            stream.close()
            return image

    def targets(self):
        return run(self.target_cmd, stdout=PIPE).stdout.decode("utf-8").splitlines()

    def paste(self, target):
        return run(self.paste_cmd + [target], stdout=PIPE, timeout=1).stdout


class WindowsClipboard(Clipboard):
    def grab(self):
        out = paste()
        if out == "":
            out = ImageGrab.grabclipboard()

        return out


class WaylandClipboard(Clipboard):
    target_cmd = ["wl-paste", "--list"]
    paste_cmd = ["wl-paste", "--type"]


class X11Clipboard(Clipboard):
    target_cmd = ["xclip", "-selection", "clipboard", "-target", "TARGETS", "-out"]
    paste_cmd = ["xclip", "-selection", "clipboard", "-out", "-target"]


def clipboard():
    return get_clipboard().grab()


def get_clipboard():
    session_list = loads(
        run(
            ["loginctl", "list-sessions", "--output=json"],
            capture_output=True,
            text=True,
        ).stdout
    )

    gui_session = [x["session"] for x in session_list if int(x["tty"][-1]) >= 5][0]
    gui_session_type = (
        run(
            ["loginctl", "show-session", gui_session, "-p", "Type"],
            capture_output=True,
            text=True,
        )
        .stdout.strip()
        .split("=")[1]
    )

    if gui_session_type == "x11":
        cls = X11Clipboard
    else:
        cls = WaylandClipboard

    return cls()

    return cls().grab()

    # def xclip(target):
    #     return run(
    #         ,
    #         stdout=PIPE,
    #     ).stdout

    # if "x11" in
    #     targets = (
    #         run(
    #            ,
    #             stdout=PIPE,
    #         )
    #         .stdout.decode("utf-8")
    #         .splitlines()
    #     )
    #     clip = xclip
    # else:
    #     targets = ()
    #     clip = wlclip
    # try:
    #     if "image/png" in targets:
    #         stream = BytesIO(clip("image/png"))
    #         image = Image.open(stream).convert("RGBA")
    #         stream.close()
    #         return image
    #     elif "" in targets:
    #         return clip("text/plain").decode("utf-8")
    #     elif not targets:
    #         info_notify("Schowek jest pusty", "'wl-clip --list' zwraca 'No selection'")
    #     else:
    #         raise NotImplementedError
    # except TimeoutExpired as err:
    #     error_notify("subprocess.TimeoutExpired", str(err))


def xdg_open(*paths):
    for path in paths:
        run(["xdg-open", path])


def dconf_write(path, value):
    if type(value) == str:
        value = f"'{value}'"
    elif type(value) == bool:
        if value:
            value = "true"
        else:
            value = "false"
    run(["dconf", "write", path, value])


def gio_icon(icon, *paths):
    for path in paths:
        path = os.path.expanduser(path)
        run(["gio", "set", "-t", "string", path, "metadata::custom-icon-name", icon])


def bashify(cmd):
    cmd = cmd.replace("'", r"\'")
    return f"bash -c '{cmd}'"
