import sublime
import sublime_plugin
import re
import threading

class OpenModuleCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        source_folder = sublime.load_settings(ModuleHighlighter.SETTINGS_FILENAME).get('source_folder', True)
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
            ismodule = bool(re.match("(include\:\:)([A-Za-z0-9+&@#/%?=~_-])*\/[-A-Za-z0-9+&@#/%?=~_()|!:,.;']*\.adoc", word))
            isxref = bool(re.match("(xref:(\.\.\/)*([-A-Za-z0-9+&@#/%?=~_()|!:,.;'])*\/(([-A-Za-z0-9+&@#/%?=~_()|!:,.;'])*\.adoc))", word))
            if ismodule:
                module = re.search("(include\:\:)([A-Za-z0-9+&@#/%?=~_-]*\/[A-Za-z0-9+&@#/%?=~_-]*\.adoc)", word).group(2)
                file_path = source_folder + module
                print ("opening " + file_path)
                self.view.window().open_file(file_path)
            if isxref:
                xref = re.search("(xref\:)(\.\.\/)*([-A-Za-z0-9+&@#/%?=~_()|!:,;']*\/[-A-Za-z0-9+&@#/%?=~_()|!:,.;']*\.adoc)", word).group(3)
                file_path = source_folder + xref
                print ("opening " + file_path)
                self.view.window().open_file(file_path)

class ModuleHighlighter(sublime_plugin.EventListener):
    #refactored from https://github.com/leonid-shevtsov/ClickableUrls_SublimeText
    #added an OR clause for xref highlighting too
    MODULE_REGEX = "(xref:(\.\.\/)*([-A-Za-z0-9+&@#/%?=~_()|!:,.;'])*\/(([-A-Za-z0-9+&@#/%?=~_()|!:,.;'])*\.adoc))|(include\:\:modules\/[-A-Za-z0-9+&@#/%?=~_()|!:,.;']*\.adoc)"
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