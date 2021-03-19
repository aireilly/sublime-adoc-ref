# sublime-adoc-ref
Sublime plugin to follow adoc references in asciidoc files.

* Copy `open_module.py` and `OpenModule.sublime-settings` to `~/.config/sublime-text-3/Packages/User/`
* Modify `OpenModule.sublime-settings` to match your asciidoc source folder 

Add a key mapping to `~/.config/sublime-text-3/Packages/User/Default (Linux).sublime-keymap`, for example:

```
[
    { "keys": ["ctrl+alt+m"], "command": "open_module" }
]