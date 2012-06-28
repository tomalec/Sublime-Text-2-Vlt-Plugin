# Written by Tomek Wytrebowicz (tomalecpub@gmail.com)
import sublime, sublime_plugin

import os
import stat
import subprocess
import tempfile
import threading

# Plugin Settings are located in 'vlt.sublime-settings' make a copy in the User folder to keep changes

# Utility functions
def ConstructCommand(in_command):
    command = ''
    if(sublime.platform() == "osx"):
        command = 'source ~/.bash_profile && '
    command += in_command
    return command

def VltCommandOnFile(in_command, in_folder, in_filename):
    command = ConstructCommand('vlt ' + in_command + ' "' + in_filename + '"')
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=in_folder, shell=True)
    result, err = p.communicate()

    if(not err):
        return 1, result.strip()
    else:
        return 0, err.strip()   

def WarnUser(message):
    vlt_settings = sublime.load_settings('vlt.sublime-settings')
    if(vlt_settings.get('vlt_warnings_enabled')):
        if(vlt_settings.get('vlt_log_warnings_to_status')):
            sublime.status_message("vlt [warning]: " + message)
        else:
            print "vlt [warning]: " + message

def LogResults(success, message):
    if(success >= 0):
        print "vlt: " + message
    else:
        WarnUser(message);
# Commit section
def Commit(in_folder, in_filename):
    # Commit the file
    return VltCommandOnFile("commit", in_folder, in_filename);

class VltAutoCommit(sublime_plugin.EventListener):
    def on_post_save(self, view):
            folder_name, filename = os.path.split(view.file_name())
            success, message = Commit(folder_name, filename)
            LogResults(success, message)

class VltCommitCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if(self.view.file_name()):
            folder_name, filename = os.path.split(self.view.file_name())
            success, message = Commit(folder_name, filename)
            LogResults(success, message)
        else:
            WarnUser("View does not contain a file")
