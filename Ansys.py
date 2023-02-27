from glob import glob
from xml.dom import minidom
from Markdown import IMAGE
import matplotlib.pyplot as plt
from os import mkdir
from slugify import slugify







def plot(df, DIR, title, **kwargs):
    if "x" in kwargs:
        ds = df.set_index(kwargs["x"]).sort_index()
        kwargs.pop("x")
    ds.plot(legend=False, **kwargs)
    filename = slugify(title)
    plt.savefig(DIR + "/" + filename)
    return IMAGE(title, DIR + "/" + filename + ".png")


def pandas_plot(df, plots, filename):
    DIR = "plots"
    try:
        mkdir(DIR)
    except FileExistsError:
        pass

    with open(filename, "w") as f:

        for k, v in plots.items():
            f.write(plot(df, DIR, k, **v))
            f.write("\n\n")


def xml_parser(dp):
    wbpj = glob("*.wbpj")[0].removesuffix(".wbpj")
    base = f"{wbpj}_files/report_files/dp{dp}/CFX/Post"
    doc = minidom.parse(f"{base}/report.xml")

    imgs = doc.getElementsByTagName("image")

    out = {}

    for i in imgs:
        title = i.attributes["name"].value
        src = f"{base}/{i.attributes['src'].value}"
        out[title] = src

    return out


def write_file(dps, filename, drop=[], include=None):
    parsed = [xml_parser(d) for d in dps]

    if isinstance(include, str):
        include = [include]

    reports = {}

    for p in parsed:
        for k, v in p.items():
            if k in reports:
                reports[k].append(v)
            else:
                reports[k] = [v]

    if include is not None:
        old = reports
        reports = {}
        for n in include:
            reports[n] = old[n]

    for d in drop:
        reports.drop(d)

    with open(filename, "w") as f:
        for k, v in reports.items():
            for i in v[:-1]:

                f.write(IMAGE("", i))
                f.write("\n")

            f.write(IMAGE(k, v[-1]))
            f.write("\n\n")
