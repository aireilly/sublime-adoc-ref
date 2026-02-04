import sublime
import sublime_plugin
import re
import os
import threading

class OpenModuleCommand(sublime_plugin.TextCommand):
    # Regex for Antora xrefs: xref:version@component:module:page.adoc[label]
    # Captures: version@, component:, module:, page.adoc, #anchor
    ANTORA_XREF_REGEX = r"xref:(?:([^@\[\]]+)@)?(?:([^:\[\]]+):)?(?:([^:\[\]]+):)?([^#\[\]]+\.adoc)(?:#([^\[\]]*))?\[([^\]]*)\]"

    # Regex for plain AsciiDoctor xrefs: xref:path/to/file.adoc#anchor[label]
    PLAIN_XREF_REGEX = r"xref:((?:\.\.\/)*(?:[^#\[\]]+\/)*[^#\[\]]+\.adoc)(?:#([^\[\]]*))?\[([^\]]*)\]"

    def run(self, edit):
        project_data = sublime.active_window().project_data()
        project_source_folder = project_data['folders'][0]['path'] if project_data else None
        if not project_source_folder:
            print("Error: No project folder found. Open a project first.")
            return

        current_file = self.view.file_name()
        current_dir = os.path.dirname(current_file) if current_file else project_source_folder

        for region in self.view.sel():
            s = self.view.substr(self.view.line(region))
            i = region.begin() - self.view.line(region).begin()
            start = 0
            end = -1
            for j, c in enumerate(s):
                if c == ' ':
                    if j < i:
                        start = j
                    else:
                        end = j
                        break
            word = s[start:end].strip() if end != -1 else s[start:].strip()

            # Check for include directive
            include_match = re.match(r"include::(.+\.(adoc|yaml|yml|txt|json))", word)
            if include_match:
                module = include_match.group(1)
                # Remove any trailing brackets from includes
                module = re.sub(r'\[.*\]$', '', module)
                print("Opening include: " + module)
                self.view.window().open_file(module)
                continue

            # Check for xref
            xref_target = self.extract_xref_target(word, current_dir, project_source_folder)
            if xref_target:
                print("Opening xref: " + xref_target)
                self.view.window().open_file(xref_target)

    def extract_xref_target(self, text, current_dir, project_root):
        """Extract the file path from an xref, supporting both Antora and plain AsciiDoctor styles."""

        # Try Antora-style xref first
        antora_match = re.match(self.ANTORA_XREF_REGEX, text)
        if antora_match:
            version = antora_match.group(1)  # e.g., "1.0"
            component = antora_match.group(2)  # e.g., "mycomponent"
            module = antora_match.group(3)  # e.g., "mymodule"
            page = antora_match.group(4)  # e.g., "mypage.adoc"
            anchor = antora_match.group(5)  # e.g., "section-id"

            # Build path based on what's provided
            return self.resolve_antora_xref(version, component, module, page, current_dir, project_root)

        # Try plain AsciiDoctor xref
        plain_match = re.match(self.PLAIN_XREF_REGEX, text)
        if plain_match:
            path = plain_match.group(1)  # e.g., "../modules/page.adoc"
            anchor = plain_match.group(2)  # e.g., "section-id"

            return self.resolve_plain_xref(path, current_dir, project_root)

        return None

    def resolve_antora_xref(self, version, component, module, page, current_dir, project_root):
        """Resolve an Antora-style xref to a file path."""

        # If only page is provided (same module), try relative to current directory
        if not component and not module:
            # Look in common Antora locations
            candidates = [
                os.path.join(current_dir, page),
                os.path.join(current_dir, "pages", page),
                os.path.join(current_dir, "..", "pages", page),
            ]
            for candidate in candidates:
                normalized = os.path.normpath(candidate)
                if os.path.exists(normalized):
                    return normalized
            # Fall back to just the page name relative to current dir
            return os.path.normpath(os.path.join(current_dir, page))

        # If module is provided but not component
        if module and not component:
            # Search for module directory in project
            search_paths = [
                os.path.join(project_root, "modules", module, "pages", page),
                os.path.join(project_root, module, "pages", page),
                os.path.join(project_root, module, page),
            ]
            for path in search_paths:
                if os.path.exists(path):
                    return path
            # Return first candidate even if not found
            return search_paths[0] if search_paths else None

        # Full Antora path with component
        if component:
            module_name = module if module else "ROOT"
            search_paths = [
                os.path.join(project_root, component, "modules", module_name, "pages", page),
                os.path.join(project_root, "docs", component, "modules", module_name, "pages", page),
            ]
            for path in search_paths:
                if os.path.exists(path):
                    return path
            return search_paths[0] if search_paths else None

        return None

    def resolve_plain_xref(self, path, current_dir, project_root):
        """Resolve a plain AsciiDoctor xref to a file path."""

        # Handle relative paths
        if path.startswith("../") or path.startswith("./"):
            return os.path.normpath(os.path.join(current_dir, path))

        # Handle absolute-like paths (from project root)
        if "/" in path:
            # Try relative to current directory first
            candidate = os.path.normpath(os.path.join(current_dir, path))
            if os.path.exists(candidate):
                return candidate
            # Try relative to project root
            return os.path.normpath(os.path.join(project_root, path))

        # Simple filename - look in current directory and common locations
        candidates = [
            os.path.join(current_dir, path),
            os.path.join(current_dir, "..", path),
            os.path.join(project_root, path),
        ]
        for candidate in candidates:
            normalized = os.path.normpath(candidate)
            if os.path.exists(normalized):
                return normalized

        # Default to current directory
        return os.path.normpath(os.path.join(current_dir, path))

class ModuleHighlighter(sublime_plugin.EventListener):
    # Refactored from https://github.com/leonid-shevtsov/ClickableUrls_SublimeText
    # Matches:
    #   - include directives: include::path/to/file.adoc[]
    #   - Antora xrefs: xref:version@component:module:page.adoc#anchor[label]
    #   - Plain xrefs: xref:path/to/file.adoc#anchor[label] or xref:file.adoc[]
    MODULE_REGEX = r"(xref:(?:[^@\[\]]+@)?(?:[^:\[\]]+:)*[^#\[\]]+\.adoc(?:#[^\[\]]*)?\[[^\]]*\])|(include::[^\[]+\.(adoc|yaml|yml|txt|json)\[[^\]]*\])"
    DEFAULT_MAX_MODULES = 200
    SETTINGS_FILENAME = 'OpenModule.sublime-settings'

    modules_for_view = {}
    scopes_for_view = {}
    ignored_views = []
    highlight_semaphore = threading.Semaphore()

    def on_activated(self, view):
        self.update_module_highlights(view)

    # Blocking handlers for ST2
    def on_load(self, view):
        if sublime.version() < '3000':
            self.update_module_highlights(view)

    def on_modified(self, view):
        if sublime.version() < '3000':
            self.update_module_highlights(view)

    # Async listeners for ST3
    def on_load_async(self, view):
        self.update_module_highlights_async(view)

    def on_modified_async(self, view):
        self.update_module_highlights_async(view)

    def on_close(self, view):
        for map in [self.modules_for_view, self.scopes_for_view, self.ignored_views]:
            if view.id() in map:
                del map[view.id()]

    """The logic entry point. Find all modules in view, store and highlight them"""
    def update_module_highlights(self, view):
        settings = sublime.load_settings(ModuleHighlighter.SETTINGS_FILENAME)
        should_highlight_modules = settings.get('highlight_modules', True)
        max_module_limit = settings.get('max_module_limit', ModuleHighlighter.DEFAULT_MAX_MODULES)

        if view.id() in ModuleHighlighter.ignored_views:
            return

        modules = view.find_all(ModuleHighlighter.MODULE_REGEX)

        # Avoid slowdowns for views with too much modules
        if len(modules) > max_module_limit:
            print("ModuleHighlighter: ignoring view with %u modules" % len(modules))
            ModuleHighlighter.ignored_views.append(view.id())
            return

        ModuleHighlighter.modules_for_view[view.id()] = modules

        should_highlight_modules = sublime.load_settings(ModuleHighlighter.SETTINGS_FILENAME).get('highlight_modules', True)
        if (should_highlight_modules):
            self.highlight_modules(view, modules)

    """Same as update_module_highlights, but avoids race conditions with a
    semaphore."""
    def update_module_highlights_async(self, view):
        ModuleHighlighter.highlight_semaphore.acquire()
        try:
            self.update_module_highlights(view)
        finally:
            ModuleHighlighter.highlight_semaphore.release()

    """Creates a set of regions from the intersection of modules and scopes,
    underlines all of them."""
    def highlight_modules(self, view, modules):
        # We need separate regions for each lexical scope for ST to use a proper color for the underline
        scope_map = {}
        for module in modules:
            scope_name = view.scope_name(module.a)
            scope_map.setdefault(scope_name, []).append(module)

        for scope_name in scope_map:
            self.underline_regions(view, scope_name, scope_map[scope_name])

        self.update_view_scopes(view, scope_map.keys())

    """Apply underlining with provided scope name to provided regions.
    Uses the empty region underline hack for Sublime Text 2 and native
    underlining for Sublime Text 3."""
    def underline_regions(self, view, scope_name, regions):
        if sublime.version() >= '3019':
            # in Sublime Text 3, the regions are just underlined
            view.add_regions(
                u'clickable-modules ' + scope_name,
                regions,
                scope_name,
                flags=sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE|sublime.DRAW_SOLID_UNDERLINE)
        else:
            # in Sublime Text 2, the 'empty region underline' hack is used
            char_regions = [sublime.Region(pos, pos) for region in regions for pos in range(region.a, region.b)]
            view.add_regions(
                u'clickable-modules ' + scope_name,
                char_regions,
                scope_name,
                sublime.DRAW_EMPTY_AS_OVERWRITE)

    """Store new set of underlined scopes for view. Erase underlining from
    scopes that were used but are not anymore."""
    def update_view_scopes(self, view, new_scopes):
        old_scopes = ModuleHighlighter.scopes_for_view.get(view.id(), None)
        if old_scopes:
            unused_scopes = set(old_scopes) - set(new_scopes)
            for unused_scope_name in unused_scopes:
                view.erase_regions(u'clickable-modules ' + unused_scope_name)

        ModuleHighlighter.scopes_for_view[view.id()] = new_scopes