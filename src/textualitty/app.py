import subprocess
import shutil
import os
import zipfile
from pathlib import Path
from rich import print, console
import urllib.request


import click
from stat import S_IXUSR, S_IXGRP, S_IXOTH

text_console = console.Console()

WORKDIR = Path(".textualitty")

ZIP_UNIX_SYSTEM = 3


def extract_all_with_executable_permission(zf, target_dir):
    for info in zf.infolist():
        extracted_path = zf.extract(info, target_dir)

        if info.create_system == ZIP_UNIX_SYSTEM and os.path.isfile(extracted_path):
            unix_attributes = info.external_attr >> 16
            if unix_attributes & S_IXUSR:
                os.chmod(
                    extracted_path,
                    os.stat(extracted_path).st_mode | S_IXUSR,
                )


@click.group()
def textualitty():
    ...


@textualitty.command()
@click.option("-v", "--verbose", is_flag=True)
def build(verbose):
    WORKDIR.mkdir(exist_ok=True)

    with text_console.status("[green]Getting latest Python Standalone"):
        urllib.request.urlretrieve(
            "https://github.com/indygreg/python-build-standalone/releases/download/20221106/cpython-3.10.8+20221106-aarch64-apple-darwin-pgo+lto-full.tar.zst",
            "python.tar.zst",
        )
    with text_console.status("[green]Extracting"):
        subprocess.run(
            "tar xvf python.tar.zst -C .textualitty".split(), capture_output=not verbose
        )

    with text_console.status("[green]Getting dependencies"):
        requirements = subprocess.run(
            "python -m pip freeze".split(), shell=False, capture_output=True
        )
        (WORKDIR / "requirements.txt").write_bytes(requirements.stdout)
        reqs = (WORKDIR / "requirements.txt").read_text()
        (WORKDIR / "requirements.txt").write_text(
            "\n".join(line for line in reqs.splitlines() if "textualitty" not in line)
            + "\ntextual"
        )

    with text_console.status("[green]Installing dependencies"):
        subprocess.run(
            f"{WORKDIR/'python'/'install'/'bin'/'python3'} -m pip install -r {WORKDIR/'requirements.txt'}".split(),
            capture_output=not verbose,
        )
    with text_console.status("[green]Getting WezTerm"):
        urllib.request.urlretrieve(
            "https://github.com/lllama/wezterm/releases/download/latest/Textualitty-macos-20221118-105315-20681e7a.zip",
            "wezterm.zip",
        )
    with text_console.status("[green]Extracting"):
        with zipfile.ZipFile("wezterm.zip") as wez:
            extract_all_with_executable_permission(wez, WORKDIR)
    with text_console.status("[green]Assembling app"):
        if (WORKDIR / "build").exists():
            (WORKDIR / "build" / ".DS_Store").unlink(missing_ok=True)
            shutil.rmtree(WORKDIR / "build")

        (WORKDIR / "build").mkdir()
        shutil.copytree(
            WORKDIR / "Textualitty-macos-20221118-105315-20681e7a" / "Textualitty.app",
            WORKDIR / "build" / "Textualitty.app",
        )
        for folder in ("bin", "lib", "include", "share"):
            shutil.copytree(
                WORKDIR / "python" / "install" / folder,
                WORKDIR / "build" / "Textualitty.app" / "Contents" / "MacOS" / folder,
            )
        shutil.copy(
            Path(__file__).parent.parent / "textual.icns",
            WORKDIR
            / "build"
            / "Textualitty.app"
            / "Contents"
            / "Resources"
            / "terminal.icns",
        )
        (
            WORKDIR
            / "build"
            / "Textualitty.app"
            / "Contents"
            / "MacOS"
            / "textualitty.py"
        ).write_text(
            """\
from textual.demo import app
app.run()
                """
        )


@textualitty.command()
@click.argument("project")
def init(project):
    print("[yellow]This doesn't do anything")


def run():
    textualitty()
