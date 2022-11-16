import subprocess
import os
import tarfile
from pathlib import Path
from rich import print, console
import urllib.request


import click

text_console = console.Console()


@click.group()
def textualitty():
    ...


@textualitty.command()
@click.option("-v", "--verbose", is_flag=True)
def build(verbose):
    # with text_console.status("[green]Building our python"):
    #     subprocess.run("pyoxidizer build".split(), capture_output=verbose)
    # with text_console.status("[green]Getting latest Python Standalone"):
    #     urllib.request.urlretrieve(
    #         "https://github.com/indygreg/python-build-standalone/releases/download/20221106/cpython-3.10.8+20221106-aarch64-apple-darwin-pgo+lto-full.tar.zst",
    #         "python.tar.zst",
    #     )
    # with text_console.status("[green]Extracting"):
    #     subprocess.run("tar xvf python.tar.zst -C .textualitty".split())

    with text_console.status("[green]Getting dependencies"):
        requirements = subprocess.run(
            "python -m pip freeze".split(), shell=False, capture_output=True
        )
        (Path(".textualitty") / "requirements.txt").write_bytes(requirements.stdout)
    with text_console.status("[green]Installing dependencies"):
        subprocess.run(
            f"{Path('.textualitty')/'python'/'install'/'bin'/'python3'} -m pip install -r {Path('.textualitty')/'requirements.txt'}".split(),
        )
        # tar = tarfile.open("python.tar.zst")
        # tar.extractall(".textualitty")
    # with text_console.status("[green]Getting WezTerm"):
    #     urllib.request.urlretrieve(
    #         "https://github.com/wez/wezterm/releases/download/20220905-102802-7d4b8249/wezterm-20220905-102802-7d4b8249-src.tar.gz",
    #         "wezterm.tar.gz",
    #     )
    # with text_console.status("[green]Extracting"):
    #     tar = tarfile.open("wezterm.tar.gz")
    #     tar.extractall(".textualitty")
    # with text_console.status("[green]Building WezTerm"):
    #     os.chdir(Path(".textualitty") / "wezterm-20220905-102802-7d4b8249")
    #     subprocess.run("./get-deps", shell=True, capture_output=verbose)
    #     subprocess.run("cargo build --release".split(), capture_output=verbose)


@textualitty.command()
@click.argument("project")
def init(project):
    subprocess.run(
        f"pyoxidizer init-config-file {project}".split(), capture_output=True
    )
    (Path(".") / project / "pyoxidizer.bzl").rename(Path(".") / "pyoxidizer.bzl")
    (Path(".") / project).rmdir()
    click.echo("config file created")


def run():
    textualitty()
