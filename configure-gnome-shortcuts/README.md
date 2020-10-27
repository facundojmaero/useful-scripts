# Gnome Shortcuts Configurator

This script configures Gnome shortcuts using a JSON file

The file can be passed as a first argument to the script, and expects an object
with a key "shortcuts" that holds the list of keybindings to configure:

```json
{
  "custom_shortcuts": [
    {
      "name": "flameshot",
      "command": "/usr/bin/flameshot gui",
      "binding": "Print",
      "builtin_replaced": "screenshot"
    }
  ],
  "builtin_shortcuts": [
    {
      "name": "next",
      "binding": "<Primary><Super>Right"
    }
  ]
}
```

Two types of shortcuts are supported:

### Builtins

Reassigns another binding to a system shortcut (like play, pause and home)

### Custom

Creates a new keybinding assigned to a custom command. Optionally disables
a builtin one.

## Just in case

If you need to do this by hand:

```bash
# Disable builtin:
gsettings set org.gnome.settings-daemon.plugins.media-keys <builtin> '[]'

# Get custom keybindings:
gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings

# Set custom keybindings:
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "[<altered_list>]"

# Configure new keybinding:
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/']"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ name 'flameshot'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ command '/usr/bin/flameshot gui'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ binding 'Print'
```
