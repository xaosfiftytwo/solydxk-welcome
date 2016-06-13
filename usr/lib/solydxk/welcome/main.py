#! /usr/bin/env python3 -OO

# Make sure the right Gtk version is loaded
import gi
gi.require_version('Gtk', '3.0')

import sys
sys.path.insert(1, '/usr/lib/solydxk/welcome')
from gi.repository import Gtk, GObject
from welcome import SolydXKWelcome
from utils import getoutput
import os
import getopt

# i18n: http://docs.python.org/3/library/gettext.html
import gettext
from gettext import gettext as _
gettext.textdomain('solydxk-welcome')

# Handle arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], 'af', ['autostart', 'force'])
except getopt.GetoptError:
    sys.exit(2)

force = False
autostart = False
for opt, arg in opts:
    print((">> opt = {} / arg = {}".format(opt, arg)))
    if opt in ('-a', '--autostart'):
        autostart = True
    elif opt in ('-f', '--force'):
        force = True


# Set variables
scriptDir = os.path.dirname(os.path.realpath(__file__))
flagPath = os.path.join(os.environ.get('HOME'), '.sws.flag')
title = _("SolydXK Welcome")
msg = _("SolydXK Welcome cannot be started in a live environment\n"
        "You can use the --force argument to start SolydXK Welcome in a live environment")


def isRunningLive():
    if force:
        return False
    liveDirs = ['/live', '/lib/live/mount', '/rofs']
    for ld in liveDirs:
        if os.path.exists(ld):
            return True
    return False


def isOEM():
    if force:
        return False
    logged_user = getoutput("logname")[0]
    if logged_user[-4:] == "-oem":
        return True
    return False


# Check if we can start
if autostart:
    if os.path.isfile(flagPath) or isRunningLive() or isOEM():
        sys.exit()


def showMsg(title, message, GtkMessageType=Gtk.MessageType.INFO):
    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, GtkMessageType, Gtk.ButtonsType.OK, message)
    dialog.set_markup("<b>{}</b>".format(title))
    dialog.format_secondary_markup(message)
    dialog.set_icon_name("solydxk")
    dialog.run()
    dialog.destroy()


# Do not run in live environment
if isRunningLive():
    showMsg(title, msg)
    sys.exit()


def uncaught_excepthook(*args):
    sys.__excepthook__(*args)
    if __debug__:
        from pprint import pprint
        from types import BuiltinFunctionType, ClassType, ModuleType, TypeType
        tb = sys.last_traceback
        while tb.tb_next: tb = tb.tb_next
        print('\nDumping locals() ...')
        pprint({k:v for k,v in tb.tb_frame.f_locals.items()
                    if not k.startswith('_') and
                       not isinstance(v, (BuiltinFunctionType,
                                          ClassType, ModuleType, TypeType))})
        if sys.stdin.isatty() and (sys.stdout.isatty() or sys.stderr.isatty()):
            try:
                import ipdb as pdb  # try to import the IPython debugger
            except ImportError:
                import pdb as pdb
            print('\nStarting interactive debug prompt ...')
            pdb.pm()
    else:
        import traceback
        title = _('Unexpected error')
        msg = _('SolydXK Welcome has failed with the following unexpected error.\nPlease submit a bug report!')
        msg = "<b>{}</b>\n\n<tt>{}</tt>".format(msg, '\n'.join(traceback.format_exception(*args)))
        showMsg(title, msg)
    sys.exit(1)

sys.excepthook = uncaught_excepthook

# main entry
if __name__ == "__main__":
    # Create an instance of our GTK application
    try:
        # Calling GObject.threads_init() is not needed for PyGObject 3.10.2+
        # Check with print (sys.version)
        # Debian Jessie: 3.4.2
        GObject.threads_init()

        SolydXKWelcome()
        Gtk.main()
    except KeyboardInterrupt:
        pass
