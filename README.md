# sublime-adoc-ref
Sublime plugin to follow adoc references in asciidoc files.

* Copy all files to `~/.config/sublime-text-3/Packages/User/`
* Modify `OpenModule.sublime-settings` > `source_folder` to match your asciidoc source folder 
* Add a key mapping to `~/.config/sublime-text-3/Packages/User/Default (Linux).sublime-keymap`, for example:

```
[
    { "keys": ["ctrl+alt+m"], "command": "open_module" }
]
```

* Also, optionally, a ctrl + mouse click shortcut is configured in `Default.sublime-mousemap`.