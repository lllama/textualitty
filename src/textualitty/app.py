import subprocess
from dataclasses import dataclass, field
import shutil
import os
import zipfile
from pathlib import Path
from rich import print, console
import urllib.request
from typing import Optional
from tomlkit import parse

import click
from stat import S_IXUSR, S_IXGRP, S_IXOTH

text_console = console.Console()

WORKDIR = Path(".textualitty")

ZIP_UNIX_SYSTEM = 3
PYTHON_STANDALONE_URL = "https://github.com/indygreg/python-build-standalone/releases/download/20221106/cpython-3.10.8+20221106-aarch64-apple-darwin-pgo+lto-full.tar.zst"
TEXTUALITTY_VERSION = "Textualitty-macos-20221122-225219-c57e88cd"

WEZTERM_URL = f"https://github.com/lllama/wezterm/releases/download/latest/{TEXTUALITTY_VERSION}.zip"


@dataclass
class Project:
    name: str
    dependencies: list = field(default_factory=list)


def get_dependencies(project: Project = None):
    if project:
        (WORKDIR / "requirements.txt").write_text("\n".join(project.dependencies))
    else:
        requirements = subprocess.run(
            "python -m pip freeze".split(), shell=False, capture_output=True
        )
        (WORKDIR / "requirements.txt").write_bytes(requirements.stdout)


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
    if (
        not WORKDIR.exists()
        or not (WORKDIR / "python").exists()
        or not (WORKDIR / TEXTUALITTY_VERSION)
    ):
        init()

    with text_console.status("[green]Updating dependencies"):
        get_dependencies()

    with text_console.status("[green]Assembling app"):
        if (WORKDIR / "build").exists():
            (WORKDIR / "build" / ".DS_Store").unlink(missing_ok=True)
            shutil.rmtree(WORKDIR / "build")

        (WORKDIR / "build").mkdir()
        shutil.copytree(
            WORKDIR / TEXTUALITTY_VERSION / "Textualitty.app",
            WORKDIR / "build" / "Textualitty.app",
        )
        for folder in ("bin", "lib", "include"):
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
        shutil.copy(
            "textualitty.py",
            WORKDIR
            / "build"
            / "Textualitty.app"
            / "Contents"
            / "MacOS"
            / "textualitty.py",
        )
        (
            WORKDIR / "build" / "Textualitty.app" / "Contents" / "MacOS" / "wezterm.lua"
        ).write_text(
            """
local wezterm = require 'wezterm'
wezterm.log_info('Config file ' .. wezterm.config_file)
return {
    default_prog = {wezterm.config_dir .. '/bin/python3', wezterm.config_dir .. '/textualitty.py'},
    hide_tab_bar_if_only_one_tab = true,
}
"""
        )
        if Path("Textualitty.app").exists():
            shutil.rmtree("Textualitty.app")

        shutil.move(WORKDIR / "build" / "Textualitty.app", "Textualitty.app")


def parse_pyproject(path):
    pyproject = parse(path.read_text())
    # Get project name
    match pyproject:
        case (
            {"tool": {"poetry": {"name": name}}} | {"tool": {"poetry": {"name": name}}}
        ):
            project = Project(name)
        case _:
            project = Project("unknown name")

    match pyproject:
        case {"project": {"dependencies": dependencies}}:
            project.dependencies = dependencies
        case {"tool": {"poetry": {"dependencies": dependencies}}}:
            export = subprocess.run(
                "poetry export -f requirements.txt".split(), capture_output=True
            )
            project.dependencies = export.stdout.decode().splitlines()

    return project


def parse_pipfile(path):
    pipfile = parse(path.read_text())
    project = Project(Path(".").resolve().name)
    match pipfile:
        case {"packages": dependencies}:
            project.dependencies = dependencies

    return project


def parse_requirements(path: Path):
    project = Project(Path(".").resolve().name)
    project.dependencies = path.read_text().splitlines()

    return project


@textualitty.command()
@click.option("-v", "--verbose", is_flag=True)
def init(verbose):
    WORKDIR.mkdir(exist_ok=True)

    if (pyproject := Path("pyproject.toml")).exists():
        project = parse_pyproject(pyproject)
    elif (pipfile := Path("Pipfile")).exists():
        project = parse_pipfile(pipfile)
    elif (requirements := Path("requirements.txt")).exists():
        project = parse_requirements(requirements)

    if not (default_py := Path("textualitty.py")).exists():
        default_py.write_text(
            """\
# This is the python file used to run your app. 
# Change as needed.
from textual.demo import app
app.run()
"""
        )

    with text_console.status("[green]Getting latest Python Standalone"):
        urllib.request.urlretrieve(
            PYTHON_STANDALONE_URL,
            "python.tar.zst",
        )
    with text_console.status("[green]Extracting"):
        subprocess.run(
            "tar xvf python.tar.zst -C .textualitty".split(), capture_output=not verbose
        )

    with text_console.status("[green]Getting dependencies"):
        get_dependencies(project)

    with text_console.status("[green]Installing dependencies"):
        subprocess.run(
            f"{WORKDIR/'python'/'install'/'bin'/'python3'} -m pip install --no-input -r {WORKDIR/'requirements.txt'}".split(),
            capture_output=not verbose,
        )
    with text_console.status("[green]Getting WezTerm"):
        urllib.request.urlretrieve(
            WEZTERM_URL,
            "wezterm.zip",
        )
    with text_console.status("[green]Extracting"):
        with zipfile.ZipFile("wezterm.zip") as wez:
            extract_all_with_executable_permission(wez, WORKDIR)


def run():
    textualitty()
