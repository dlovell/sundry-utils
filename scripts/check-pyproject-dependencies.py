#! /usr/bin/env nix-shell
#! nix-shell -i python3 --packages "with python310Packages; [ attrs click poetry-core tomli toolz ]"

import functools
import itertools
import pathlib

import click
import tomli
import toolz
from attr import (
    field,
    frozen,
)
from attr.validators import (
    instance_of,
)
from poetry.core.packages.dependency import Dependency


@frozen
class PoetryDependencies:
    path = field(validator=instance_of(pathlib.Path), converter=pathlib.Path)
    dependency_keys = ("tool", "poetry", "dependencies")

    @staticmethod
    def make_dep(name, python_versions=None, **kwargs):
        dep = Dependency(name, **kwargs)
        if python_versions is not None:
            dep.python_versions = python_versions
        return dep

    @property
    @functools.cache
    def toml(self):
        return tomli.loads(self.path.read_text())

    @property
    def python_versions(self):
        return toolz.get_in(self.dependency_keys + ("python",), self.toml)

    @property
    @functools.cache
    def dependencies(self):
        def rename_key(from_, to_, dct):
            if from_ in dct:
                dct = toolz.assoc(
                    toolz.dissoc(dct, from_),
                    to_,
                    dct[from_],
                )
            return dct
        (from_, to_) = "version", "constraint"
        deps = (
            self.make_dep(name, python_versions=self.python_versions, **dct)
            for name, dct in (
                (name, rename_key(from_, to_, dct) if isinstance(dct, dict) else {to_: dct})
                for name, dct in toolz.get_in(self.dependency_keys, self.toml).items()
                if name != "python"
            )
        )
        return deps

    @property
    def required(self):
        return tuple(dep for dep in self._deps if not dep.is_optional())

    @property
    def optional(self):
        return tuple(dep for dep in self._deps if dep.is_optional())


@frozen
class PipDependencies:
    path = field(validator=instance_of(pathlib.Path), converter=pathlib.Path)
    required_dependency_keys = ("project", "dependencies")
    optional_dependency_keys = ("project", "optional-dependencies")

    @staticmethod
    def make_dep(line, optional=False):
        dep = Dependency.create_from_pep_508(line)
        dep._optional = optional
        return dep

    @property
    @functools.cache
    def toml(self):
        return tomli.loads(self.path.read_text())

    @property
    @functools.cache
    def dependencies(self):
        deps = itertools.chain(
            (
                self.make_dep(line, optional=False)
                for line in toolz.get_in(self.required_dependency_keys, self.toml)
            ),
            (
                # optionals are grouped by "extra" name
                self.make_dep(line, optional=True)
                for line in itertools.chain(*toolz.get_in(self.optional_dependency_keys, self.toml).values())
            ),
        )
        return deps

    @property
    def required(self):
        return tuple(dep for dep in self._deps if not dep.is_optional())

    @property
    def optional(self):
        return tuple(dep for dep in self._deps if dep.is_optional())


def get_discrepancies(path):
    left = {dep.name: dep for dep in PipDependencies(path).dependencies}
    right = {dep.name: dep for dep in PoetryDependencies(path).dependencies}
    discrepancies = {
        name: (ldep, rdep)
        for (name, ldep, rdep) in (
            (name, left.get(name), right.get(name))
            for name in sorted(left | right)
        )
        if ldep != rdep
    }
    return discrepancies


@click.command
@click.option(
    "--path",
    type=str,
    default="./pyproject.toml",
    required=True,
    help="The path to the pyproject.toml to check"
)
def print_discrepancies(path):
    print(get_discrepancies(path))


if __name__ == "__main__":
    print_discrepancies()
