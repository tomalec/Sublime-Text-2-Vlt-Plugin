# Written by Tomek Wytrebowicz (tomalecpub@gmail.com)
# TODO: vlt add directories (-N non recursive)
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
    preSaveIsFileInRepo = 0
    def on_pre_save(self, view):
        vlt_settings = sublime.load_settings('vlt.sublime-settings')

        self.preSaveIsFileInRepo = 0

        # check if this part of the plugin is enabled
        if(not vlt_settings.get('vlt_auto_add')):
            WarnUser("Auto Add disabled")
            return

        folder_name, filename = os.path.split(view.file_name())
        self.preSaveIsFileInRepo = IsFileInRepo(folder_name, filename)

    def on_post_save(self, view):
        if(self.preSaveIsFileInRepo == -1):
            folder_name, filename = os.path.split(view.file_name())
            success, message = Add(folder_name, filename)
            LogResults(success, message)
        else:
            if(not sublime.load_settings('vlt.sublime-settings').get('vlt_auto_commit')):
                WarnUser("Auto Commit disabled")
            return
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

# Add section
def Add(in_folder, in_filename):
    # Add the file
    success, message = VltCommandOnFile("add", in_folder, in_filename);

    if(not success or message[0:2]!="A "):
        return 0, message
    return VltCommandOnFile("ci", in_folder, in_filename);

class VltAddCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if(self.view.file_name()):
            folder_name, filename = os.path.split(self.view.file_name())
            success, message = Add(folder_name, filename)
            LogResults(success, message)
        else:
            WarnUser("View does not contain a file")

def IsFileInRepo(in_folder, in_filename):
    success, message =  VltCommandOnFile("info", in_folder, in_filename);
    if(not success):
        return 0, message
    # locate the line containing "Status: " and extract the following status
    startindex = message.find("Status: ")
    if(startindex == -1):
        WarnUser("Unexpected output from 'vlt info'.")
        return -1
    
    startindex += 8 # advance after "Status: "

    endindex = message.find("\n", startindex) 
    if(endindex == -1):
        WarnUser("Unexpected output from 'vlt info'.")
        return -1

    status = message[startindex:endindex].strip();
    if(os.path.isfile(os.path.join(in_folder, in_filename))): # file exists on disk, not being added
        if(status != "unknown"):
            return 1
        else:
            return 0
    else:
        if(status != "unknown"):
            return -1 # will be in the depot, it's being added
        else:
            return 0


# Update section
def Update(in_folder, in_filename):
    # update the file
    return VltCommandOnFile("update", in_folder, in_filename);

class VltUpdateCommand(sublime_plugin.TextCommand):
    def run(self, edit): 
        if(self.view.file_name()):
            folder_name, filename = os.path.split(self.view.file_name())

            if(IsFileInRepo(folder_name, filename)):
                success, message = Update(folder_name, filename)
            else:
                success = 0
                message = "File is not in the repo."

            LogResults(success, message)
        else:
            WarnUser("View does not contain a file")