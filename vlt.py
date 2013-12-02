# Written by Tomek Wytrebowicz (tomalecpub@gmail.com)
# TODO: vlt add directories (-N non recursive)
import os
import sublime
import sublime_plugin
import tempfile
import threading
import subprocess
import functools
import os.path
import time
import shutil

# Plugin Settings are located in 'vlt.sublime-settings' make a copy in the User folder to keep changes
 
# when sublime loads a plugin it's cd'd into the plugin directory. Thus
# __file__ is useless for my purposes. What I want is "Packages/Git", but
# allowing for the possibility that someone has renamed the file.
# Fun discovery: Sublime on windows still requires posix path separators.
PLUGIN_DIRECTORY = os.getcwd().replace(os.path.normpath(os.path.join(os.getcwd(), '..', '..')) + os.path.sep, '').replace(os.path.sep, '/')


vlt_root_cache = {}
def vlt_root(directory):
    global vlt_root_cache

    retval = False
    leaf_dir = directory

    if leaf_dir in vlt_root_cache and vlt_root_cache[leaf_dir]['expires'] > time.time():
        return vlt_root_cache[leaf_dir]['retval']

    while directory:
        if os.path.exists(os.path.join(directory, '.vlt')):
            retval = directory
        else:
            #break with last directory containing .vlt
            if retval != False:
                break

        parent = os.path.realpath(os.path.join(directory, os.path.pardir))
        if parent == directory:
            # /.. == /
            retval = False
            break

        directory = parent

    vlt_root_cache[leaf_dir] = { 'retval': retval, 'expires': time.time() + 5 }

    return retval

# Utility functions
def ConstructCommand(in_command):
    command = ''
    if(sublime.platform() == "osx"):
        command = 'source ~/.bash_profile && '
    command += in_command
    return command

def VltCommandOnFile(in_command, in_folder, in_filename):
    # Per http://bugs.python.org/issue8557 shell=True is required to
    # get $PATH on Windows. Yay portable code.
    shell = os.name == 'nt'

    vlt_command = sublime.load_settings("vlt.sublime-settings").get('vlt_command') or 'vlt'
    command = ConstructCommand(vlt_command+' ' + in_command + ' "' + in_filename + '"')
    print "vlt [debug]: " + (vlt_root(in_folder) or "[no-vlt repo]") + ': '+ command
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=in_folder, shell=shell)
    result, err = p.communicate()
    
    if(not err):
        return 1, result.strip()
    else:
        return 0, err.strip()   

def main_thread(callback, *args, **kwargs):
    # sublime.set_timeout gets used to send things onto the main thread
    # most sublime.[something] calls need to be on the main thread
    sublime.set_timeout(functools.partial(callback, *args, **kwargs), 0)
def _make_text_safeish(text, fallback_encoding, method='decode'):
    # The unicode decode here is because sublime converts to unicode inside
    # insert in such a way that unknown characters will cause errors, which is
    # distinctly non-ideal... and there's no way to tell what's coming out of
    # git in output. So...
    try:
        unitext = getattr(text, method)('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        unitext = getattr(text, method)(fallback_encoding)
    return unitext

class CommandThread(threading.Thread):
    def __init__(self, command, on_done, working_dir="", fallback_encoding="", **kwargs):
        threading.Thread.__init__(self)
        self.command = command
        self.on_done = on_done
        self.working_dir = working_dir
        if "stdin" in kwargs:
            self.stdin = kwargs["stdin"]
        else:
            self.stdin = None
        if "stdout" in kwargs:
            self.stdout = kwargs["stdout"]
        else:
            self.stdout = subprocess.PIPE
        self.fallback_encoding = fallback_encoding
        self.kwargs = kwargs

    def run(self):
        try:
            # Per http://bugs.python.org/issue8557 shell=True is required to
            # get $PATH on Windows. Yay portable code.
            shell = os.name == 'nt'
            if self.working_dir != "":
                os.chdir(self.working_dir)

            proc = subprocess.Popen(self.command,
                stdout=self.stdout, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                shell=shell, universal_newlines=True)
            output = proc.communicate(self.stdin)[0]
            if not output:
                output = ''
            # if sublime's python gets bumped to 2.7 we can just do:
            # output = subprocess.check_output(self.command)
            main_thread(self.on_done,
                _make_text_safeish(output, self.fallback_encoding), **self.kwargs)
        except subprocess.CalledProcessError, e:
            main_thread(self.on_done, e.returncode)
        except OSError, e:
            if e.errno == 2:
                main_thread(sublime.error_message, "Vlt binary could not be found in PATH\n\nConsider using the vlt_command setting for the vlt plugin\n\nPATH is: %s" % os.environ['PATH'])
            else:
                raise e

# Draft A base for all commands
class VltCommand(object):
    may_change_files = False

    def run_command(self, command, callback=None, show_status=True,
            filter_empty_args=True, no_save=False, **kwargs):
        if filter_empty_args:
            command = [arg for arg in command if arg]
        if 'working_dir' not in kwargs:
            kwargs['working_dir'] = self.get_working_dir()
        if 'fallback_encoding' not in kwargs and self.active_view() and self.active_view().settings().get('fallback_encoding'):
            kwargs['fallback_encoding'] = self.active_view().settings().get('fallback_encoding').rpartition('(')[2].rpartition(')')[0]

        s = sublime.load_settings("vlt.sublime-settings")
        if s.get('save_first') and self.active_view() and self.active_view().is_dirty() and not no_save:
            print "vlt[debug] save first" 
            self.active_view().run_command('save')
        if command[0] == 'vlt' and s.get('vlt_command'):
            command[0] = s.get('vlt_command')
        #if not callback:
        #    callback = self.generic_done
        print "vlt[debug]: " + ' '.join(command)

        thread = CommandThread(command, callback, **kwargs)
        thread.start()

        if show_status:
            message = kwargs.get('status_message', False) or ' '.join(command)
            sublime.status_message(message)


    def _output_to_view(self, output_file, output, clear=False,
            syntax="Packages/Diff/Diff.tmLanguage", **kwargs):
        output_file.set_syntax_file(syntax)
        edit = output_file.begin_edit()
        if clear:
            region = sublime.Region(0, self.output_view.size())
            output_file.erase(edit, region)
        output_file.insert(edit, 0, output)
        output_file.end_edit(edit)

    def scratch(self, output, title=False, position=None, **kwargs):
        scratch_file = self.get_window().new_file()
        if title:
            scratch_file.set_name(title)
        scratch_file.set_scratch(True)
        self._output_to_view(scratch_file, output, **kwargs)
        scratch_file.set_read_only(True)
        if position:
            sublime.set_timeout(lambda: scratch_file.set_viewport_position(position), 0)
        return scratch_file

    def panel(self, output, **kwargs):
        if not hasattr(self, 'output_view'):
            self.output_view = self.get_window().get_output_panel("vlt")
        self.output_view.set_read_only(False)
        self._output_to_view(self.output_view, output, clear=True, **kwargs)
        self.output_view.set_read_only(True)
        self.get_window().run_command("show_panel", {"panel": "output.vlt"})

    def quick_panel(self, *args, **kwargs):
        self.get_window().show_quick_panel(*args, **kwargs)

# A base for all vlt commands that work with the entire repository
class VltWindowCommand(VltCommand, sublime_plugin.WindowCommand):
    def active_view(self):
        return self.window.active_view()

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()

    @property
    def fallback_encoding(self):
        if self.active_view() and self.active_view().settings().get('fallback_encoding'):
            return self.active_view().settings().get('fallback_encoding').rpartition('(')[2].rpartition(')')[0]

    # If there's no active view or the active view is not a file on the
    # filesystem (e.g. a search results view), we can infer the folder
    # that the user intends Vlt commands to run against when there's only
    # only one.
    def is_enabled(self):
        if self._active_file_name() or len(self.window.folders()) == 1:
            return vlt_root(self.get_working_dir())

    def get_file_name(self):
        return ''

    # If there is a file in the active view use that file's directory to
    # search for the Vlt root.  Otherwise, use the only folder that is
    # open.
    def get_working_dir(self):
        file_name = self._active_file_name()
        if file_name:
            return os.path.realpath(os.path.dirname(file_name))
        else:
            try: # handle case with no open folder
                return self.window.folders()[0]
            except IndexError:
                return ''

    def get_window(self):
        return self.window

class VltStatusCommand(VltWindowCommand):
    force_open = False

    def run(self):
        #self.run_command(['vlt', 'status' ], self.status_done)
        self.run_command(['vlt', 'status', vlt_root(self.get_working_dir()) ], self.status_done, True)

    def status_done(self, result):
        self.results = filter(self.status_filter, result.rstrip().split('\n'))
        if len(self.results):
            self.show_status_list()
        else:
            sublime.status_message("Nothing to show")

    def show_status_list(self):
        self.quick_panel(self.results, self.panel_done,
            sublime.MONOSPACE_FONT)

    def status_filter(self, item):
        # for this class we don't actually care
        return len(item) > 0

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_file = self.results[picked]
        # first 2 characters are status codes, the third is a space
        picked_status = picked_file[:1]
        picked_file = picked_file[2:]
        self.panel_followup(picked_status, picked_file, picked)

    def panel_followup(self, picked_status, picked_file, picked_index):
        # split out solely so I can override it for laughs

        s = sublime.load_settings("Vlt.sublime-settings")
        #root = vlt_root(self.get_working_dir())
        #vlt even if asked for other destination always prints paths relative to current working dir
        root = self.get_working_dir()
        #get rid of (mime/type)
        picked_file = picked_file.split(" (")[0]
        if picked_status == '?' or picked_status == 'A' or picked_status == 'C' or s.get('status_opens_file') or self.force_open:
            if(os.path.isfile(os.path.join(root, picked_file))): self.window.open_file(os.path.join(root, picked_file))
        else:
            self.run_command(['vlt', 'diff', picked_file.strip('"')],
                self.diff_done, working_dir=root)

    def diff_done(self, result):
        if not result.strip():
            return
        self.scratch(result, title="Vlt Diff")


def WarnUser(message):
    vlt_settings = sublime.load_settings('vlt.sublime-settings')
    if(vlt_settings.get('vlt_warnings_enabled')):
        if(vlt_settings.get('vlt_log_warnings_to_status')):
            sublime.status_message("vlt [warning]: " + message)
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

# A base for all vlt commands that work with the file in the active view
class VltTextCommand(VltCommand, sublime_plugin.TextCommand):
    def active_view(self):
        return self.view

    def is_enabled(self):
        # First, is this actually a file on the file system?
        if self.view.file_name() and len(self.view.file_name()) > 0:
            return vlt_root(self.get_working_dir())

    def get_file_name(self):
        return os.path.basename(self.view.file_name())

    def get_working_dir(self):
        return os.path.realpath(os.path.dirname(self.view.file_name()))

    def get_window(self):
        # Fun discovery: if you switch tabs while a command is working,
        # self.view.window() is None. (Admittedly this is a consequence
        # of my deciding to do async command processing... but, hey,
        # got to live with that now.)
        # I did try tracking the window used at the start of the command
        # and using it instead of view.window() later, but that results
        # panels on a non-visible window, which is especially useless in
        # the case of the quick panel.
        return self.view.window() or sublime.active_window()
        # So, this is not necessarily ideal, but it does work.

class VltCommitAllCommand(VltTextCommand):
    def run(self, edit):
        self.run_command(['vlt', 'commit'], self.commit_done, True)

    def commit_done(self, result):
        if result.strip():
            self.scratch(result, title="Vlt Commit", syntax=plugin_file("syntax/Vlt Status.tmLanguage"))
        else:
            sublime.status_message("Nothing to show")


class VltCommitCommand(VltTextCommand):
    def run(self, edit):
        self.run_command(['vlt', 'commit', os.path.join(self.get_working_dir(), self.get_file_name())], 
            self.commit_done, True, status_message="Commiting...")

    def commit_done(self, result, **kwargs):
        print "vlt[debug]: " + result
        sublime.status_message("Commiting... "+ result.splitlines()[-1])


class VltAutoCommit(sublime_plugin.EventListener):
    preSaveIsFileInRepo = 0
    def on_pre_save(self, view): 
        vlt_settings = sublime.load_settings('vlt.sublime-settings')

        self.preSaveIsFileInRepo = 0
        # check if this part of the plugin is enabled
        if not vlt_settings.get('vlt_auto_add'):
            WarnUser("Auto Add disabled")
            return
        self.preSaveIsFileInRepo = IsFileInRepo(view.file_name())
    def on_post_save(self, view):
        if(self.preSaveIsFileInRepo == -1):
            folder_name, filename = os.path.split(view.file_name())
            success, message = Add(folder_name, filename)
            LogResults(success, message)
        else:
            vlt_settings = sublime.load_settings('vlt.sublime-settings')
            if not vlt_settings.get('vlt_auto_commit'):
                WarnUser("Auto commit disabled")
                return
            view.run_command('vlt_commit')

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

class VltAddChoiceCommand(VltStatusCommand):
#VltStatusCommand):
    def status_filter(self, item):
        return item[0]=="?"

    def show_status_list(self):
        self.results = [[" + All Files", "apart from untracked files"]] + self.results
        self.quick_panel(self.results, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_followup(self, picked_status, picked_file, picked_index):
        working_dir=self.get_working_dir()

        if picked_index == 0:
            command = ['vlt', 'add', vlt_root(working_dir)]
        else:
            command = ['vlt']
            picked_file = picked_file.strip('"')
            #if os.path.isfile(working_dir+"/"+picked_file):
            command += ['add']
            #else:
            #    command += ['rm']
            command += [picked_file]

        self.run_command(command, self.rerun,
            working_dir=working_dir)

    def rerun(self, result):
        self.run()


def IsFileInRepo(filename):
    in_folder, in_filename = os.path.split(filename)
    success, message =  VltCommandOnFile("info", in_folder, in_filename);
    if(not success):
        return 0, message
    # locate the line containing "Status: " and extract the following status
    startindex = message.find("Status: ")
    if(startindex == -1):
        WarnUser("Unexpected output from 'vlt info'.")
        return -1
    
    startindex += 8 # advance after "Status: "

    endindex = message.find('\n', startindex) 
    if(endindex == -1):
        status = message[startindex:].strip();
    else:
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

class VltUpdateCommand(VltTextCommand):
    def run(self, edit): 
        if(self.view.file_name()):
            if(IsFileInRepo(self.view.file_name())):
                self.run_command(['vlt', 'update', self.view.file_name() ], self.update_done, True)
            else:
                WarnUser("File is not in the repo.")
        else:
            WarnUser("View does not contain a file")
    def update_done(self, result):
        print "vlt[debug]: " + result
        self.view.run_command("revert")
        sublime.status_message("File updated")


class VltUpdateAllCommand(VltWindowCommand):
    force_open = False

    def run(self):
        self.run_command(['vlt', 'update', vlt_root(self.get_working_dir()) ], self.update_done, True)

    def update_done(self, result):
        if result.strip():
            self.scratch(result, title="Vlt Update",
                syntax=plugin_file("syntax/Vlt Status.tmLanguage"))
        else:
            sublime.status_message("Nothing to show")

class VltUpdateAllForceCommand(VltUpdateAllCommand):
    def run(self):
        self.run_command(['vlt', 'update', vlt_root(self.get_working_dir()), '--force' ], self.update_done, True)
    

class VltResolveCommand(VltTextCommand):
    def run(self, edit):
        self.run_command(['vlt', 'res', os.path.join(self.get_working_dir(), self.get_file_name())], self.commit_done, True)

    def commit_done(self, result):
        if result.strip():
            self.scratch(result, title="Vlt Update",
                syntax=plugin_file("syntax/Vlt Status.tmLanguage"))
        else:
            sublime.status_message(result)

class VltRemoveCommand(VltTextCommand):
    def run(self, edit):
        self.run_command(['vlt', 'rm', os.path.join(self.get_working_dir(), self.get_file_name())], self.commit_done, True)

    def commit_done(self, result):
        sublime.status_message(result)


class VltRevertChoiceCommand(VltStatusCommand):
#VltStatusCommand):
    def show_status_list(self):
        self.results = [[" - All Files", "revert all files"]] + self.results
        self.quick_panel(self.results, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_followup(self, picked_status, picked_file, picked_index):
        working_dir=self.get_working_dir()
        command = ['vlt', 'revert']
        if picked_index == 0:
            command += ['-R', vlt_root(working_dir)]
            self.run_command(command, self.show_output, working_dir=working_dir)
        else:
            #get rid of (mime/type)
            picked_file = picked_file.strip('"').split(" (")[0]
            #if os.path.isfile(working_dir+"/"+picked_file):
            #   command += ['revert']
            #else:
            #    command += ['rm']
            command += [picked_file]

            self.run_command(command, self.rerun, working_dir=working_dir)

    def rerun(self, result):
        self.run()
    def show_output(self, result):
        self.scratch(result, title="Vlt Revert",
                syntax=plugin_file("syntax/Vlt Status.tmLanguage"))


def plugin_file(name):
    return os.path.join(PLUGIN_DIRECTORY, name)


#TODO: aggregate it in one vlt process log.
class VltRenameCommand(VltTextCommand):
    def run(self, edit):
        view = self.active_view()
        window = self.get_window()
        window.show_input_panel("New name", os.path.basename( view.file_name() ),
            self.rename, self.on_change, self.on_cancel)
    def rename(self, input):
        view = self.active_view()
        file = view.file_name()
        shutil.copy2(file, input)
        folder_name, filename = os.path.split(file)
        success, message = Add(folder_name, input)
        
        LogResults(success, message)

        if(not success):
            return 0, message
        
        self.run_command(['vlt', 'rm', os.path.join(self.get_working_dir(), self.get_file_name())], self.commit, 
            True, status_message="Renaming...",
            file = file)

    def commit(self, result, file, **kwargs):
        self.run_command(['vlt', 'commit', file], self.scratch, 
            True, status_message="Commiting...", title="Vlt Rename", 
            syntax=plugin_file("syntax/Vlt Status.tmLanguage"))


    def on_change(self, input):
        pass

    def on_cancel(self):
        pass
