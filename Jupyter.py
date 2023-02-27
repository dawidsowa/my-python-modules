import pandas as pd
from pathlib import Path

# from slugify import slugify
from IPython.display import Markdown, display
from subprocess import run
import matplotlib.pyplot as plt


def format_numeric(df, formats=None, default_format="{:.1f}"):
    """Format the numeric columns of a Pandas DataFrame.

    Args:
        df (pd.DataFrame): The Pandas DataFrame to be formatted.
        formats (dict): A dictionary of column names and format strings to be applied to the corresponding columns.
        default_format (str): The default format string to be applied to columns that are not specified in `formats`.
            Defaults to "0.0f".

    Returns:
        pd.DataFrame: The input Pandas DataFrame with the specified numeric columns formatted as strings.
    """

    def format_numeric_column(col):
        if col.name in formats:
            fmt = formats[col.name]
        else:
            fmt = default_format
        return col.apply(lambda x: str(fmt.format(x)) if isinstance(x, float) else x)

    return df.fillna("").apply(format_numeric_column).style.format(na_rep="")


def subscript_names(s):
    match s[0]:
        case "P" | "Q" | "m" | "W":
            return f"{s[0]}_{{{s[1:]}}}"
        case _:
            return s


def latexify_names(lis):

    return [f"${subscript_names(l)}$" for l in lis]


def _df_to_md(df, file, title, dir="media", **kwargs):
    file = Path(dir) / file

    if "fontsize" in kwargs:
        fontsize = kwargs["fontsize"]
        del kwargs["fontsize"]
    else:
        fontsize = None

    string = df.to_markdown(**kwargs)

    with file.open("w") as f:
        if fontsize:
            f.write(f"\{fontsize}")
            f.write("\n\n")
        f.write(string)
        f.write("\n\n")
        f.write("Table: " + title)
        if fontsize:
            f.write("\n")
            f.write(f"\\normalsize")

    return Markdown(string)


def to_md(object, file=None, title=None, **kwargs):
    match type(object):
        case pd.core.frame.DataFrame:
            return _df_to_md(object, file, title, **kwargs)


def set_column_font(col, size, reset="normalsize"):
    return [f"\\{size} {x} \{reset}" for x in col]


# def savemd(title, height=None, id=None):

#     plt.close()
#     args = ""
#     if height is not None:
#         args += f"height={height}"
#     if id is not None:
#         args += f" #fig:{id}"
#     return display(
#         Markdown(f"![{title}]({filename}){'{' +args + '}'if args != '' else args}")
#     )


def writeNotebook(filename, defaults="default"):
    out = run(
        [
            "jupyter",
            "nbconvert",
            "--to",
            "markdown",
            "--TemplateExporter.exclude_input=True",
            f"{filename}.ipynb",
        ],
        capture_output=True,
    )

    run(["pandoc", f"{filename}.md", "-o", f"{filename}.pdf", "--defaults", defaults])
