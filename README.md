# Follow asciidoc ref

![adoc follow](adoc-follow.gif)

Sublime plugin that allows you to navigate to `include::` and `xref::` asciidoc references in asciidoc files.


1. Add the project to Sublime Text package control.
2. Install the newly added package.

* Download the repo files and unzip. 
* Copy all files to `~/.config/sublime-text-3/Packages/User/`
* Add a source folder to `~/.config/sublime-text-3/Packages/User/OpenModule.sublime-settings`, for example `"source_folder": "~/openshift-docs/"`.
* Add a key mapping to `~/.config/sublime-text-3/Packages/User/Default (Linux).sublime-keymap`, for example:
```
[
    { "keys": ["ctrl+alt+m"], "command": "open_module" }
]
```

* Also, optionally, configure a [ctrl + mouse click] shortcut in `Default.sublime-mousemap`, for example: 
```
[
    {
        "button": "button1", 
        "count": 1, 
        "modifiers": ["ctrl"],
        "press_command": "drag_select",
        "command": "open_module"
    }
]
```
