#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

GET = "gsettings get"
SET = "gsettings set"
SCHEMADIR = "org.gnome.settings-daemon.plugins.media-keys"
CUSTOM_SCHEMADIR = f"{SCHEMADIR}.custom-keybinding"


@dataclass
class BaseShortcut:
    """Dataclass that holds the structure of a shortcut"""

    name: str
    binding: str


@dataclass
class BuiltinShortcut(BaseShortcut):
    """Dataclass that holds the structure of a shortcut"""

    pass


@dataclass
class CustomShortcut(BaseShortcut):
    """Dataclass that holds the structure of a shortcut"""

    command: str

    builtin_replaced: str = None
    index: int = None


class ShortcutManager:
    """Class that handles the creation and edition of shortcuts"""

    def __init__(self, config_path: str) -> None:
        """Class constructor

        Read the config file and looks for custom shortcuts already configured

        Args:
            config_path (str): Path to the configuration file to apply
        """

        json_config = self._read_config_file(config_path)
        custom_shortcuts = json_config.get("custom_shortcuts", [])
        builtin_shortcuts = json_config.get("builtin_shortcuts", [])

        self.custom_shortcuts = self._parse_custom(data=custom_shortcuts)
        self.builtin_shortcuts = self._parse_builtin(data=builtin_shortcuts)
        self.current_shortcuts = self._read_current_shortcuts()

    def configure_builtin_shortcuts(self):
        """Configure the builtin shortcuts defined in the config file"""
        for shortcut in self.builtin_shortcuts:
            cmd = f"{SET} {SCHEMADIR} {shortcut.name} '[\"{shortcut.binding}\"]'"
            subprocess.call(["/bin/bash", "-c", cmd])

    def configure_custom_shortcuts(self):
        """Configure the custom shortcuts defined in the config file"""

        shortcuts_to_apply = self._compute_shortcuts_to_apply(
            current=self.current_shortcuts,
            requested=self.custom_shortcuts,
        )

        for shortcut in shortcuts_to_apply:
            if shortcut.builtin_replaced:
                self._disable_builtin_shortcut(builtin=shortcut.builtin_replaced)

            self._configure_shortcut(shortcut=shortcut)

    def _compute_shortcuts_to_apply(
        self,
        current: Dict[str, CustomShortcut],
        requested: Dict[str, CustomShortcut],
    ) -> List[CustomShortcut]:
        """Given a current and requested list of shortcuts, checks if there's a name
        match. In that case, that shortcut has to be edited, not created

        Args:
            current (Dict[str, CustomShortcut]): Current custom shortcuts
            requested (Dict[str, CustomShortcut]): Requested custom shortcuts

        Returns:
            List[CustomShortcut]: List of shortcuts to apply
        """

        names_current = current.keys()
        names_requested = requested.keys()
        shortcuts_in_common = set(names_current).intersection(names_requested)

        for name in shortcuts_in_common:
            requested[name].index = current[name].index
        return [s for s in requested.values()]

    def _configure_shortcut(self, shortcut: CustomShortcut) -> None:
        """Actually configures a new shortcut by making the required syscalls

        Creates a new one if needed, and then configures the name, binding and command

        Args:
            shortcut (Shortcut): Shortcut to configure
        """

        if shortcut.index is None:
            # create new shortcut
            new_shortcut_list = self._get_new_shortcut_list()
            shortcut.index = len(new_shortcut_list) - 1

            cmd = f'{SET} {SCHEMADIR} custom-keybindings "{new_shortcut_list}"'

            subprocess.call(["/bin/bash", "-c", cmd])

        shortcut_name = f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom{shortcut.index}/"

        commands = [
            f"{SET} {CUSTOM_SCHEMADIR}:{shortcut_name} name {shortcut.name}",
            f"{SET} {CUSTOM_SCHEMADIR}:{shortcut_name} binding {shortcut.binding}",
            f'{SET} {CUSTOM_SCHEMADIR}:{shortcut_name} command "{shortcut.command}"',
        ]

        for cmd in commands:
            subprocess.call(["/bin/bash", "-c", cmd])

    def _disable_builtin_shortcut(self, builtin: str) -> None:
        """Disables a builtin shortcut

        Args:
            builtin (str): Name of the builtin to disable
        """
        cmd = f"{SET} {SCHEMADIR} {builtin} '[]'"
        subprocess.call(["/bin/bash", "-c", cmd])

    def _parse_builtin(self, data: Dict[str, str]) -> List[BuiltinShortcut]:
        """Parse a dictionary into a list of BuiltinShortcuts

        Args:
            data (Dict[str, str]): Dictionary with desired builtin shortcuts

        Returns:
            List[BuiltinShortcut]: List of parsed shortcuts
        """
        try:
            builtin_shortcuts = [BuiltinShortcut(**obj) for obj in data]
        except Exception as e:
            print(f"Error parsing a builtin shortcut {e}")
            sys.exit(1)
        else:
            return builtin_shortcuts

    def _parse_custom(self, data: Dict[str, str]) -> Dict[str, CustomShortcut]:
        """Parse a dictionary into a dict of CustomShortcuts

        Args:
            data (Dict[str, str]): Dictionary with desired custom shortcuts

        Returns:
            Dict[str, CustomShortcut]: List of parsed shortcuts
        """
        try:
            custom_shortcuts = {obj["name"]: CustomShortcut(**obj) for obj in data}
        except Exception as e:
            print(f"Error parsing a custom shortcut {e}")
            sys.exit(1)

        return custom_shortcuts

    def _build_shortcut_struct(self, shortcut_name: str, index: int) -> CustomShortcut:
        """Get a CustomShortcut that's already defined in the system

        Args:
            shortcut_name (str): The shortcut name to retrieve
            index (int): The shortcut index

        Returns:
            CustomShortcut: The retrieved shortcut
        """
        base_cmd = f"{GET} {CUSTOM_SCHEMADIR}:{shortcut_name}"

        name_cmd = f"{base_cmd} name"
        binding_cmd = f"{base_cmd} binding"
        command_cmd = f"{base_cmd} command"

        name = (
            subprocess.check_output(["/bin/bash", "-c", name_cmd])
            .decode("utf-8")
            .strip()
            .strip("'")
        )
        binding = (
            subprocess.check_output(["/bin/bash", "-c", binding_cmd])
            .decode("utf-8")
            .strip()
            .strip("'")
        )
        command = (
            subprocess.check_output(["/bin/bash", "-c", command_cmd])
            .decode("utf-8")
            .strip()
            .strip("'")
        )

        return CustomShortcut(name=name, binding=binding, command=command, index=index)

    def _read_current_shortcuts(self) -> Dict[str, CustomShortcut]:
        """Read current custom shortcuts defined in the system

        Returns:
            Dict[str, CustomShortcut]: CustomShortcuts already defined
        """
        cmd = f"{GET} {SCHEMADIR} custom-keybindings"
        output = subprocess.check_output(["/bin/bash", "-c", cmd]).decode("utf-8")
        stripped = output.lstrip("@as")  # If the list was empty, strip "@as"
        custom_shortcut_list = eval(stripped)

        shortcuts = {}

        for i, name in enumerate(custom_shortcut_list):
            shortcut = self._build_shortcut_struct(shortcut_name=name, index=i)
            shortcuts[shortcut.name] = shortcut

        return shortcuts

    def _read_config_file(self, config_path: str) -> Dict:
        """Read the config file with shortcut definitions

        Args:
            config_path (str): Path to the config file

        Returns:
            Dict: The contents of the config file
        """

        path = Path(config_path)

        if not path.exists() or not path.is_file():
            print(f"Error, the file {path} was not found")
            sys.exit(1)

        with path.open("r") as f:
            try:
                raw_file = json.load(f)
            except Exception as e:
                print(f"Error, the file {path} is not a valid JSON file")
                print(e)
                sys.exit(1)
            else:
                return raw_file

    def _get_new_shortcut_list(self) -> List[str]:
        """Get the list of custom shortcuts, and append the one that will be created

        Returns:
            List[str]: List of custom shortcuts
        """
        cmd = f"{GET} {SCHEMADIR} custom-keybindings"
        output = subprocess.check_output(["/bin/bash", "-c", cmd]).decode("utf-8")
        stripped = output.lstrip("@as")  # If the list was empty, strip "@as"
        current_shortcut_list = eval(stripped)

        new_shortcut_path = self._get_new_shortcut_path(current_shortcut_list)
        new_shortcut_list = current_shortcut_list + [new_shortcut_path]

        return new_shortcut_list

    def _get_new_shortcut_path(self, current_list: List[str]) -> str:
        """Generate the name of the new shortcut

        Simply appends `base` with a number that doesn't clash with the ones already in
        the list, using its lenght.

        Args:
            current_list (List[str]): Current list of custom shortcuts

        Returns:
            str: Name of the new shortcut
        """
        base = (
            "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom{}/"
        )
        return base.format(len(current_list))


parser = argparse.ArgumentParser()
parser.add_argument("config_file", help="The configuration file to apply")


def main():
    """Main script function. Does all the hard work"""
    args = parser.parse_args()

    manager = ShortcutManager(args.config_file)
    manager.configure_custom_shortcuts()
    manager.configure_builtin_shortcuts()


if __name__ == "__main__":
    main()
