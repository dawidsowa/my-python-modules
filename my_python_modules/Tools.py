from configparser import ConfigParser

# import inotify.adapters
from pathlib import Path
from os.path import expanduser
from glob import glob as _glob
from xdg.DesktopEntry import DesktopEntry


ignore = [".config/Code"]


def watch_dir(path, func=lambda x, y, _: print(x, y), types="IN_CLOSE_WRITE"):
    i = inotify.adapters.InotifyTree(path)
    for event in i.event_gen(yield_nones=False):
        (_, type_names, dir, filename) = event
        dir = Path(dir)
        if types in type_names:
            func(dir, dir / filename, type_names)


def glob(path):
    return [Path(g) for g in _glob(expanduser(path))]


def symlink(path: Path, target: Path, executable=False, verbose=False):
    path = path.expanduser()
    target = target.expanduser()

    if path.is_symlink() and path.readlink() != target:
        path.unlink()

    if not path.exists():
        if verbose:
            print(f"{path.name} -> {target}")
        path.symlink_to(target)

    if executable:
        target.chmod(0o744)

    return path


def mass_file_creator(files: dict, dry_run=False, verbose=False):
    created_files = []

    if dry_run:
        verbose = True
    for path, v in files.items():
        path = Path(path).expanduser()

        if not isinstance(v, dict):
            v = {"text": v}
        # Symlink
        if "target" in v:
            symlink(path, **v)

        elif isinstance(v["text"], ConfigParser):
            if verbose:
                print(f"Zapisuję INI do {path.name}")

            if dry_run:
                continue

            v["text"].write(path.open("w"), space_around_delimiters=False)
            created_files.append(path)

        if "post_cmd" in v:
            if not isinstance(v["post_cmd"], list):
                v["post_cmd"] = [v["post_cmd"]]

            for cmd in v["post_cmd"]:
                cmd(path)

    return created_files


def dict_to_ini(dic: dict):
    ini = ConfigParser(interpolation=None)
    ini.optionxform = str
    ini.read_dict(dic)
    return ini


def ini(path):
    ini = ConfigParser(interpolation=None)
    print(path)
    ini.read_file(str(path))
    return ini


def get_icon(path, default="inode-directory"):
    conf = Path(path) / ".directory"
    if conf.exists():
        try:
            de = DesktopEntry(conf)
            return de.getIcon()
        except:
            return default
    else:
        return default


class FileDeleter:
    existing_files = []
    created_files = []

    def capture(self, dir):
        dir = Path(dir)
        self.existing_files = [x for x in dir.iterdir() if x.is_file()]

    def files(self, files):
        self.created_files = files

    def delete(self):
        for x in [x for x in self.existing_files if x not in self.created_files]:
            print(f"Usuwam {x.name}")
            x.unlink()

    def append(self, file):
        self.created_files.append(file)
