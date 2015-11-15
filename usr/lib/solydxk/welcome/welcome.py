#! /usr/bin/env python3

# from gi.repository import Gtk, GdkPixbuf, GObject, Pango, Gdk, GLib
from gi.repository import Gtk, Gdk, GObject, GLib
from os.path import join, abspath, dirname, basename, exists
from utils import ExecuteThreadedCommands, hasInternetConnection, getoutput
from simplebrowser import SimpleBrowser
import os
from dialogs import MessageDialogSafe
from queue import Queue

# i18n: http://docs.python.org/3/library/gettext.html
import gettext
from gettext import gettext as _
gettext.textdomain('solydxk-welcome')

# Need to initiate threads for Gtk
GObject.threads_init()


#class for the main window
class SolydXKWelcome(object):

    def __init__(self):

        # ================================

        # Define html page array
        # 0 = no action (just show)
        # 1 = apt install
        # 2 = open external application
        # 3 = backports
        self.pages = []
        self.pages.append([0, 'welcome'])
        self.pages.append([2, 'drivers'])
        self.pages.append([1, 'multimedia'])
        self.pages.append([3, 'libreoffice'])
        self.pages.append([1, 'business'])
        self.pages.append([1, 'home'])
        self.pages.append([1, 'system'])
        self.pages.append([1, 'games'])
        self.pages.append([1, 'wine'])

        # ================================

        # Load window and widgets
        self.scriptName = basename(__file__)
        self.scriptDir = abspath(dirname(__file__))
        self.mediaDir = join(self.scriptDir, '../../../share/solydxk/welcome')
        self.htmlDir = join(self.mediaDir, "html")
        self.builder = Gtk.Builder()
        self.builder.add_from_file(join(self.mediaDir, 'welcome.glade'))

        # Main window objects
        go = self.builder.get_object
        self.window = go("welcomeWindow")
        self.swWelcome = go("swWelcome")
        self.btnInstall = go("btnInstall")
        self.btnQuit = go("btnQuit")
        self.btnNext = go("btnNext")
        self.btnPrevious = go("btnPrevious")
        self.pbWelcome = go("pbWelcome")

        self.window.set_title(_("SolydXK Welcome"))
        self.btnInstall.set_label(_("Install"))
        self.btnQuit.set_label(_("Quit"))
        self.btnNext.set_label(_("Next"))
        self.btnPrevious.set_label(_("Previous"))

        self.btnInstall.set_sensitive(False)
        self.btnPrevious.set_sensitive(False)

        # Resize the window to 65% of the screen size
        s = Gdk.Screen.get_default()
        w = s.get_width()
        h = s.get_height()
        if w > 640:
            self.window.set_default_size(w * 0.75, h * 0.75)
        else:
            self.window.fullscreen()

        # Initiate variables
        self.queue = Queue(-1)
        self.threads = {}
        self.currentPage = 0
        self.flagPath = os.path.join(os.environ.get('HOME'), '.sws.flag')
        self.lastPage = len(self.pages) - 1
        self.languageDir = self.get_language_dir()
        self.pbSavedState = 0
        self.nextSavedState = True
        self.prevSavedState = False

        # Check for backports
        self.isBackportsEnabled = False
        output = getoutput("grep backports /etc/apt/sources.list | grep -v ^#")
        if output:
            self.isBackportsEnabled = True
        else:
            output = getoutput("grep backports /etc/apt/sources.list.d/*.list | grep -v ^#")
            if output:
                self.isBackportsEnabled = True

        # Load first HTML page
        self.loadHtml(self.pages[0][1])

        # Connect builder signals and show window
        self.builder.connect_signals(self)
        self.window.show_all()

    # ===============================================
    # Main window functions
    # ===============================================

    def on_btnInstall_clicked(self, widget):
        actionNr = self.pages[self.currentPage][0]
        if actionNr > 0:
            # Check if there is an internet connection
            if not hasInternetConnection():
                title = _("No internet connection")
                msg = _("You need an internet connection to install the additional software.\n"
                        "Please, connect to the internet and try again.")
                MessageDialogSafe(title, msg, Gtk.MessageType.WARNING, self.window).show()
                return

            self.set_buttons_state(False)

            # Check for installation script
            msg = _("Please enter your password")
            page = self.pages[self.currentPage][1]
            script = join(self.scriptDir, "scripts/{}".format(page))
            if exists(script):
                if actionNr == 1 or actionNr == 3:
                    self.exec_command("gksudo -m \"{}\" \"/bin/sh -c {}\"".format(msg, script))
                elif actionNr == 2:
                    os.system("/bin/sh -c \"{}\" &".format(script))
                    self.set_buttons_state(True)
            else:
                msg = _("Cannot install the requested software:\n"
                        "Script not found: {}".format(script))
                MessageDialogSafe(self.btnInstall.get_label(), msg, Gtk.MessageType.ERROR, self.window).show()

    def on_btnQuit_clicked(self, widget):
        self.on_welcomeWindow_destroy(widget)

    def on_btnPrevious_clicked(self, widget):
        self.switchPage(-1)

    def on_btnNext_clicked(self, widget):
        self.switchPage(1)

    def switchPage(self, count):
        self.currentPage += count

        # Skip backport page if system is not enabled for backports
        if self.pages[self.currentPage][0] == 3 and not self.isBackportsEnabled:
            if count > 0:
                self.switchPage(1)
            else:
                self.switchPage(-1)
            return

        self.btnInstall.set_sensitive(self.pages[self.currentPage][0])
        self.btnPrevious.set_sensitive(self.currentPage)
        self.btnNext.set_sensitive(self.currentPage - self.lastPage)
        self.loadHtml(self.pages[self.currentPage][1])
        if self.currentPage > 0:
            self.pbWelcome.set_fraction(1 / (self.lastPage / self.currentPage))
        else:
            self.pbWelcome.set_fraction(0)
        if not self.btnNext.get_sensitive():
            self.btnPrevious.grab_focus()
        elif not self.btnPrevious.get_sensitive():
            self.btnNext.grab_focus()

    def loadHtml(self, page):
        page = "{}/{}.html".format(self.languageDir, page)
        if exists(page):
            url = "file://{}".format(page)
            children = self.swWelcome.get_children()
            if children:
                children[0].openUrl(url)
            else:
                self.swWelcome.add(SimpleBrowser(url))

    def get_language_dir(self):
        # First test if full locale directory exists, e.g. html/pt_BR,
        # otherwise perhaps at least the language is there, e.g. html/pt
        lang = self.get_current_language()
        path = os.path.join(self.htmlDir, lang)
        if path != self.htmlDir:
            if not os.path.isdir(path):
                path = os.path.join(self.htmlDir, lang.split('_')[0].lower())
                if not os.path.isdir(path):
                    return os.path.join(self.htmlDir, 'en')
            return path
        # else, just return English slides
        return os.path.join(self.htmlDir, 'en')

    def get_current_language(self):
        return os.environ.get('LANG', 'US').split('.')[0]

    def show_message(self, cmdOutput, onlyOnError=False):
        try:
            msg = _("There was an error during the installation.\n"
                    "Please, run 'sudo apt-get -f install' in a terminal.\n"
                    "Visit our forum for support: http://forums.solydxk.com")
            if int(cmdOutput) != 255:
                if int(cmdOutput) > 0:
                    # There was an error
                    MessageDialogSafe(self.btnInstall.get_label(), msg, Gtk.MessageType.ERROR, self.window).show()
                elif not onlyOnError:
                    msg = _("The software has been successfully installed.")
                    MessageDialogSafe(self.btnInstall.get_label(), msg, Gtk.MessageType.INFO, self.window).show()
        except:
            MessageDialogSafe(self.btnInstall.get_label(), cmdOutput, Gtk.MessageType.INFO, self.window).show()

    def exec_command(self, command):
        try:
            # Run the command in a separate thread
            print(("Run command: {}".format(command)))
            name = 'aptcmd'
            t = ExecuteThreadedCommands([command], self.queue)
            self.threads[name] = t
            t.daemon = True
            t.start()
            self.queue.join()
            GLib.timeout_add(250, self.check_thread, name)

        except Exception as detail:
            MessageDialogSafe(self.btnInstall.get_label(), detail, Gtk.MessageType.ERROR, self.window).show()

    def set_buttons_state(self, enable):
        if not enable:
            # Get widgets current state
            self.nextSavedState = self.btnNext.get_sensitive()
            self.prevSavedState = self.btnPrevious.get_sensitive()
            self.pbSavedState = self.pbWelcome.get_fraction()

            # Disable buttons and pulse the progressbar
            self.btnInstall.set_sensitive(False)
            self.btnNext.set_sensitive(False)
            self.btnPrevious.set_sensitive(False)
        else:
            # Set widgets back to old state
            self.pbWelcome.set_fraction(self.pbSavedState)
            self.btnNext.set_sensitive(self.nextSavedState)
            self.btnPrevious.set_sensitive(self.prevSavedState)
            self.btnInstall.set_sensitive(True)

    def check_thread(self, name):
        if self.threads[name].is_alive():
            self.pbWelcome.pulse()
            if not self.queue.empty():
                ret = self.queue.get()
                print((">> Queue returns: {}".format(ret)))
                self.queue.task_done()
                self.show_message(ret, True)
            return True

        # Thread is done
        print(("++ Thread is done"))
        if not self.queue.empty():
            ret = self.queue.get()
            self.queue.task_done()
            self.show_message(ret)
        del self.threads[name]

        self.set_buttons_state(True)

        return False

    # Close the gui
    def on_welcomeWindow_destroy(self, widget):
        # Create flag file
        print(('touch {}'.format(self.flagPath)))
        os.system('touch {}'.format(self.flagPath))
        # Close the app
        Gtk.main_quit()
