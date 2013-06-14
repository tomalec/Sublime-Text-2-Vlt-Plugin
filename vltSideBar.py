import sublime, sublime_plugin
import os

import vlt


class VltSideBarAddCommand(sublime_plugin.WindowCommand):
    def run(self, paths = []):
        for path in paths:        	
            folder_name, filename = os.path.split(path)
            vlt.VltCommandOnFile("add", folder_name, filename);

    def is_enabled(self, paths = []):
        return True

    def is_visible(self, paths =[]):
        return True
        
class VltSideBarUpdateCommand(sublime_plugin.WindowCommand):
    def run(self, paths = []):
    	#TODO aggregate it into one scratch, VltUpdateAllCommand
        for path in paths:          
            folder_name, filename = os.path.split(path)
            vlt.VltCommandOnFile("update", folder_name, filename);

    def is_enabled(self, paths = []):
        return True

    def is_visible(self, paths =[]):
        return True
        
class VltSideBarCommitCommand(sublime_plugin.WindowCommand):
    def run(self, paths = []):
        #TODO aggregate it into one scratch, VltCommitAllCommand
        for path in paths:          
            folder_name, filename = os.path.split(path)
            vlt.VltCommandOnFile("commit", folder_name, filename);

    def is_enabled(self, paths = []):
        return True

    def is_visible(self, paths =[]):
        return True

class VltSideBarRemoveCommand(sublime_plugin.WindowCommand):
    def run(self, paths = []):
        #TODO aggregate it into one scratch, VltRemoveCommand
        for path in paths:          
            folder_name, filename = os.path.split(path)
            vlt.VltCommandOnFile("rm", folder_name, filename);

    def is_enabled(self, paths = []):
        return True

    def is_visible(self, paths =[]):
        return True

