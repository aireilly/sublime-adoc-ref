import sublime
import sublime_plugin
import re

source_folder = '~/openshift-docs/'

class OpenModuleCommand(sublime_plugin.TextCommand):

    def run(self, edit):
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
            ismodule = bool(re.match("include\:\:modules\/[-A-Za-z0-9+&@#/%?=~_()|!:,.;']*\.adoc\[leveloffset=\+[0-9]\]", word))
            if ismodule:
                module = re.search("modules\/[-A-Za-z0-9+&@#/%?=~_()|!:,.;']*\.adoc", word).group(0)
                file_path = source_folder + module
                print ("opening " + file_path)
                self.view.window().open_file(file_path)