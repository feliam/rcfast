#!/usr/bin/env python


import ConfigParser
from subprocess import Popen, PIPE
import sys
import pygtk
import gtk
import gobject
import threading
import time
import os
import xmlrpclib
import random
from platform import platform

#Load the mini debuger
if platform().startswith('win') or platform().startswith('Win'):
   from tester_win import test
elif 'inux' in platform():
   from tester_lin import test



class WorkerThread(threading.Thread):
    def __init__(self, commandline, normal_data, crash_data, extension, timeout, sendkeys_list, backup_folders, log, done):
        threading.Thread.__init__ (self)
        self.log = log
        self.done = done
        self.commandline = commandline
        self.normal_data = normal_data
        self.crash_data = crash_data
        self.extension = extension
        self.timeout = timeout
        self.sendkeys_list = sendkeys_list
        self.stopthread = threading.Event()
        self.backup_folders = backup_folders

    def test(self, data):
        return test( self.commandline,
                            data.encode('base64'),
                            self.extension,
                            self.timeout,
                            self.sendkeys_list,
                            self.backup_folders)

    def run(self):
        try:
            self.log("[I] Checking Normal file don't crash...\n")
            test_result = self.test(self.normal_data)
            if "Closed: CRASHED!" in test_result:
                raise Exception("Normal file SHALL not crash!")
            self.log("done.\n")

            self.log("[I] Checking Crash file DO crash...")
            test_result = self.test(self.crash_data)
            if not "Closed: CRASHED!" in test_result:
                raise Exception("Crashed file SHALL crash!")
            self.log("done.\n")
            self.log(''.join(['[C] '+x+'\n' for x in test_result.split('\n')]))


            minimal_data = self.crash_data
            self.log("[I] Calculating minimal differencies...")
            diff = [ i for i in range(0,len(minimal_data)) if minimal_data[i] != self.normal_data[i] ]
            self.log(" done. There are %d differencies.\n"%len(diff))
            self.log("[I] Differencies:\n")
            self.log(''.join([ '[I] \t%d: %02x %02x\n'%(i,ord(self.normal_data[i]),ord(minimal_data[i])) for i in diff ]))


            lr = 0.5
            MAXITERATIONS=1000
            self.log("[I] Learning rate of %f\n"%lr)
            self.log("[I] Maximun number of iterations: %d\n"%MAXITERATIONS)

            for i in xrange(0,MAXITERATIONS):
                if self.stopthread.isSet():
                    break
                new_size = int(len(diff)*lr)
                new_diff = random.sample(diff, new_size)

                self.log("[I] Iteration: %d\n"%i)
                self.log("[I] \tOriginal number of diffs: %d\n"%len(diff))
                self.log("[I] \tNew number of diffs: %d\n"%new_size)
                self.log("[I] \tLearning rate: %f\n"%lr)
                self.log("[I] \tApplying %d diffs to temporary stream..."%new_size) 
                test_data = list(self.normal_data)
                for j in new_diff:
                    test_data[j] = self.crash_data[j]
                test_data = ''.join(test_data)
                self.log("done.\n")

                self.log("[I] Testing...")
                test_result = self.test(minimal_data)
                self.log("done.\n")
                if "Closed: CRASHED!" in test_result:
                    diff = new_diff
                    lr = lr <= 0.1 and 0.05 or lr - 0.05
                    try:
                        instruction = test_result[test_result.find('Instruction:')+13:].split('\n')[0]
                    except Exception,e:
                        instruction = str(e)
                    #self.log(''.join(['[C] '+x+'\n' for x in test_result.split('\n')]))
                    self.log("[I] \tCrashing instruction: %s\n"%instruction)
                    self.log("[I] \tIt crashed, saving partial results!\n")
                    minimal_data = test_data
                    self.log("[I] A solution with %d differences found in %d iterations.\n"%(len(new_diff),i))
                    partial_filename = "minimal-%ddiff%s"%(len(new_diff),self.extension)
                    file(partial_filename,"wb").write(minimal_data)
                    self.log("[I] Partial solution saved in file: %s\n"%partial_filename)

                else:
                    lr = lr >= 0.9 and 0.99 or lr + 0.05
                    self.log("[I] \tIt didn't crashed, increasing lr to %f\n"%lr)



                if len(new_diff) <20:
                    self.log("[I] Found a solution with less than 20 mods, stop...\n")
                    break
            #End MAXITERATINS LOOP

            self.log("[I] Calculating minimal differencies...")
            diff = [ i for i in range(0,len(minimal_data)) if minimal_data[i] != self.normal_data[i] ]
            self.log(" done. There are %d differencies.\n"%len(diff))
            self.log("[I] Differencies:\n")
            self.log(''.join([ '[I] \t%d: %02x %02x\n'%(i,ord(self.normal_data[i]),ord(minimal_data[i])) for i in diff ]))


            self.log("[I] Trying reduce it bit by bit ...\n")
            co = 0
            for i in xrange(0,len(minimal_data)):
                if self.stopthread.isSet():
                    break
                if self.normal_data[i] != minimal_data[i]:
                    co+=1
                    self.log("[I] (%d/%d) Byte @%d differ (%02x != %02x)\n"%(co,len(diff),i,ord(self.normal_data[i]),ord(minimal_data[i])))
                    self.log("[I] Testing without this mod @%d ..."%i)

                    test_case = minimal_data[:i]+self.normal_data[i]+minimal_data[i+1:]
                    test_result = self.test(test_case)
                    self.log("done. Result: ")
                    if "Closed: CRASHED!" in test_result:
                        self.log("CRASHED!\n")
                        self.log("[I] \tIt crashes without mod @%d\n"%i) 
                        minimal_data = test_case

                        self.log("[I] Calculating minimal differencies...")
                        diff = [ i for i in range(0,len(minimal_data)) if minimal_data[i] != self.normal_data[i] ]
                        self.log(" done. There are %d differencies.\n"%len(diff))
                        self.log("[I] Differencies:\n")
                        self.log(''.join([ '[I] \t%d: %02x %02x\n'%(i,ord(self.normal_data[i]),ord(minimal_data[i])) for i in diff ]))

                        partial_filename = "minimal-%ddiff%s"%(len(diff),self.extension)
                        file(partial_filename,"wb").write(minimal_data)
                        self.log("[I] Partial solution saved in file: %s\n"%partial_filename)
                    else:
                        self.log("[I] \tIt wont crash without mod @%d. Keeping mutation.\n"%i)

            self.log("[I] Calculating minimal differencies...")
            diff = [ i for i in range(0,len(minimal_data)) if minimal_data[i] != self.normal_data[i] ]
            self.log(" done. There are %d differencies.\n"%len(diff))
            self.log("[I] Differencies:\n")
            self.log(''.join([ '[I] \t%d: %02x %02x\n'%(i,ord(self.normal_data[i]),ord(minimal_data[i])) for i in diff ]))

        except Exception,e:
            result = str(e)
        
        if self.stopthread.isSet():
            result = "Canceled!"
        else:
            result = "Done!"
        gobject.idle_add(self.done, result)


    def stop(self):
        self.stopthread.set()

class RCFGtk:
    """This is the Reduce Crash Fast GTK application"""
    #############################################################################
    ## Configuration file conveniencies
    def _config_load(self, default={}):
        self.config = ConfigParser.SafeConfigParser(defaults={'timeout':'10'})
        self.config.read(["rcfast.ini"])
    def _config_save(self):
        self.config.write(file("rcfast.ini","w"))

    def _config_list(self, section = 'main'):
        return [section+"."+x for x in self.config.options(section.upper())]

    def _config_get(self, feature, default=None):
        if not feature.count('.'):
            section = 'main'
        else:
            section, feature = feature.split('.')
        try:
            return self.config.get(section.upper(), feature.upper())
        except:
            return default
    def _config_set(self, feature, value):
        if not feature.count('.'):
            section = 'main'
        else:
            section, feature = feature.split('.')
        try:
            self.config.add_section(section.upper())
        except:
            pass
        return self.config.set(section.upper(), feature.upper(), str(value))


    def playsound(self, soundfile):
        try:
            from platform import platform
            if platform().startswith('win') or platform().startswith('Win'):
                from winsound import PlaySound, SND_FILENAME, SND_ASYNC
                PlaySound(soundfile, SND_FILENAME|SND_ASYNC)
            elif 'inux' in platform():
                from wave import open as waveOpen
                from ossaudiodev import open as ossOpen
                s = waveOpen(soundfile,'rb')
                (nc,sw,fr,nf,comptype, compname) = s.getparams( )
                dsp = ossOpen('/dev/dsp','w')
                try:
                    from ossaudiodev import AFMT_S16_NE
                except ImportError:
                    if byteorder == "little":
                        AFMT_S16_NE = ossaudiodev.AFMT_S16_LE
                    else:
                        AFMT_S16_NE = ossaudiodev.AFMT_S16_BE
                dsp.setparameters(AFMT_S16_NE, nc, fr)
                data = s.readframes(nf)
                s.close()
                dsp.write(data)
                dsp.close()
        except Exception,e:
            print str(e)
            pass

    def on_button_jorge_clicked(self, widget, data=None):
        self.playsound("./sounds/lenda.wav")

    def on_MainWindow_destroy(self, widget, data=None):
        if self.running == True:
            self.worker.stop()
            self.running = False
            self.rworker = False
        gtk.main_quit()
        self._config_save()


    def on_filechooserbutton_application_fileset(self, widget, data=None):
        #Todo check it is executable and readeable
        application = widget.get_filename()
        self.message("Selected application: %s"%application)
        self._config_set("application",application)

    def on_filechooserbutton_normal_fileset(self, widget, data=None):
        normal_filename = widget.get_filename()
        crash_filename = self.builder.get_object("filechooserbutton_crashing").get_filename()
        self.message("Normal file selected: %s"%normal_filename)
        self.normal_data = None
        try:
            self.normal_data = file(normal_filename,"rb").read()
        except:
            pass
        if self.normal_data == None or len(self.normal_data)==0:
            self.error("Couldn't read %s"%(normal_filename))
            widget.set_filename("(none)")
        else:
            self.message("Read %d bytes of normal file %s"%(len(self.normal_data),normal_filename))
            if self.crash_data != None:
                normal_base, normal_extension = os.path.splitext(normal_filename)
                crash_base, crash_extension = os.path.splitext(crash_filename)
                if crash_extension != normal_extension:
                    self.warning("Extensions differ %s != %s (Using %s)"%(normal_extension,crash_extension,normal_extension))
                if len(self.normal_data) != len(self.crash_data):
                    self.warning("Normal file size (%s) differs from crash file size(%d)."%(len(self.normal_data),len(self.crash_data)))
            #optional fun
            try:
                self.log(Popen("file "+crash_filename, shell=True,stdout=PIPE).communicate()[0])
            except:
                pass


    def on_filechooserbutton_crashing_fileset(self, widget, data=None):
        crash_filename = widget.get_filename()
        normal_filename = self.builder.get_object("filechooserbutton_crashing").get_filename()
        self.crash_data = None
        try:
            self.crash_data = file(crash_filename,"rb").read()
        except:
            pass
        if self.crash_data == None:
            self.error("couldn't read %s"%(crash_filename))
            widget.set_filename("(none)")
        else:
            self.message("Read %d bytes of crash file %s"%(len(self.crash_data),crash_filename))

            if self.normal_data != None :
                normal_base, normal_extension = os.path.splitext(normal_filename)
                crash_base, crash_extension = os.path.splitext(crash_filename)
                if crash_extension != normal_extension:
                    self.warning("Extensions differ %s != %s (Using %s)"%(normal_extension,crash_extension,normal_extension))
                if len(self.normal_data) != len(self.crash_data):
                    self.warning("Normal file size (%s) differs from crash file size(%d)."%(len(self.normal_data),len(self.crash_data)))
            try:
                self.log(Popen("file "+crash_filename, shell=True,stdout=PIPE).communicate()[0])
            except:
                pass


    def on_spinbutton_timeout_valuechanged(self, widget, data=None):
        timeout = widget.get_value()
        send_keys_timeout = self.builder.get_object("spinbutton_sendkeys_timeout").get_value()
        if self.builder.get_object("checkbutton_keystrokes").get_active() and send_keys_timeout >= timeout:
            self.warning("Sendkeys timer hits after program timeout")
            widget.set_value(send_keys_timeout)
        else:
            self.message("Timeout changed to % 3d secs"%timeout)
            self._config_set("timeout", timeout)

    def on_spinbutton_sendkeys_timeout_valuechanged(self, widget, data=None):
        timeout = self.builder.get_object("spinbutton_timeout").get_value()
        send_keys_timeout = widget.get_value()
        if send_keys_timeout >= timeout:
            self.warning("Sendkeys timeout occurs after program timeout")
            widget.set_value(timeout)
        else:
            send_keys_timeout = widget.get_value()
            self.message("Sendkeys timer changed to % 3.2f secs"%send_keys_timeout)



    def on_button_reduce_clicked(self, widget, data=None):
        def log(text):
            self.log(text)
        def done(text):
            self.running = False
            self.worker = None
            self.builder.get_object("button_cancel").set_sensitive(self.running)
            self.builder.get_object("button_reduce").set_sensitive(not self.running)
            self.message(text)

        if self.running == True:
            raise Exception("Already running??")
        if self.worker != None:
            raise Exception("Already running?? (worker != None)")

        if self.builder.get_object("filechooserbutton_application").get_filename() == None:
            self.error("Please select an application first!")
            self.builder.get_object("notebook").set_current_page(0)
            self.worker = None
            return
        if self.builder.get_object("filechooserbutton_normal").get_filename() == None or self.normal_data == None:
            self.error("Please select the non-crashing file first!")
            self.builder.get_object("notebook").set_current_page(0)
            return
        if self.builder.get_object("filechooserbutton_crashing").get_filename() == None or self.crash_data == None:
            self.error("Please select the crashing file first!")
            self.builder.get_object("notebook").set_current_page(0)
            return
        if len(self.crash_data) != len(self.normal_data):
            self.builder.get_object("notebook").set_current_page(0)
            self.error("Both the normal and the crashing file SHALL have the sme size!")
            return

        assert self.running == False and self.worker == None

        self.builder.get_object("notebook").set_current_page(1)

        self.running = True

        normal_filename = self.builder.get_object("filechooserbutton_crashing").get_filename()
        crash_filename = self.builder.get_object("filechooserbutton_crashing").get_filename()
        normal_base, normal_extension = os.path.splitext(normal_filename)
        application = self.builder.get_object("filechooserbutton_application").get_filename()
        timeout = self.builder.get_object("spinbutton_timeout").get_value()

        if self.builder.get_object("checkbutton_keystrokes").get_active():
            repeate = self.builder.get_object("radiobutton_repeat").get_active()
            sendkeys_timeout = self.builder.get_object("spinbutton_sendkeys_timeout").get_value()
            sendkeys = self.builder.get_object("entry_sendkeys").get_text()
            sendkeys_list=[(sendkeys_timeout,repeate,sendkeys)]
        else:
            sendkeys_list=[]

        if self.builder.get_object("checkbutton_backup_folder").get_active():
            backup_folders = [ self.builder.get_object("filechooserbutton_backup_folder").get_filename()]
        else:
            backup_folders = []

        self.worker = WorkerThread( commandline = [application, "$TESTFILE"],
                                    normal_data=self.normal_data,
                                    crash_data=self.crash_data, 
                                    extension=normal_extension,
                                    timeout=timeout,
                                    sendkeys_list=sendkeys_list, backup_folders=backup_folders,
                                    log=log,done=done)
        print "WORKER SET!"

        self.worker.start()
        self.builder.get_object("button_cancel").set_sensitive(self.running)
        self.builder.get_object("button_reduce").set_sensitive(not self.running)

    def on_button_cancel_clicked(self, widget, data=None):
        assert self.running == True
        self.worker.stop()
        self.worker = None


    def on_MainWindows_key(self, widget, data=None):
        if data.keyval==65293:
            if self.running:
                self.on_button_cancel_clicked(widget, data=None)
            else:
                self.on_button_reduce_clicked(widget, data=None)
        elif data.keyval in [106,74]:
            self.playsound("sounds/lenda.wav")

    def on_notebook_change_current_page(self, widget, data=None):
        pass

    def on_checkbutton_keystrokes_toggled(self, widget, data=None):
        self.enable_sendkeys(widget.get_active())

    def on_checkbutton_backup_folder_toggled(self, widget, data=None):
        self.builder.get_object("filechooserbutton_backup_folder").set_sensitive(widget.get_active())
        self._config_set("backup.folder_enabled",widget.get_active())

    def on_entry_sendkeys_changed(self, widget, data=None):
        sendkeys = widget.get_text()
        self.message("Keys to send: %s"%sendkeys)
        self._config_set("sendkeys.keystrokes", sendkeys)

    def on_radiobutton_once_toggled(self, widget, data=None):
        self._config_set("sendkeys.repeat",self.builder.get_object("radiobutton_repeat").get_active())
    def on_radiobutton_repeate_toggled(self, widget, data=None):
        self._config_set("sendkeys.repeat",self.builder.get_object("radiobutton_repeat").get_active())

    def on_filechooserbutton_backup_folder_selection_changed(self, widget, data=None):
        self._config_set("backup.folder", widget.get_filename())

    def status(self,text):
        statusbar = self.builder.get_object("statusbar")
        context_id = statusbar.get_context_id("main")
        while not statusbar.pop(context_id) is None:
            pass
        statusbar.push(context_id,text=text)

    def log(self,text):
        textview_log = self.builder.get_object("textview_log")
        text_buffer = textview_log.get_buffer()
        text_buffer.insert(text_buffer.get_end_iter(),text)
        textview_log.scroll_to_iter(text_buffer.get_end_iter(),0.0)

    def warning(self,text):
        self.status(text)
        self.log("[W] "+text+"\n")
    def error(self,text):
        self.status(text)
        self.log("[E] "+text+"\n")
    def message(self,text):
        self.status(text)
        self.log("[I] "+text+"\n")


    def enable_sendkeys(self, enabled=True):
        for name in ["radiobutton_repeat","radiobutton_once",
                     "spinbutton_sendkeys_timeout","entry_sendkeys"]:
            self.builder.get_object(name).set_sensitive(enabled)
        self._config_set("sendkeys.enabled",enabled)


    def __init__(self):

        #Set the Glade file
        filename = "rcfast.ui"  
        self.builder = gtk.Builder()
        self.builder.add_from_file(filename)
        unconnected = self.builder.connect_signals(self)
        assert unconnected is None

        #Set filter of program selection
        filelilter_application = self.builder.get_object("filefilter_application")
        filelilter_application.add_pattern("*.exe")

        #The application to run
        self.normal_data = None
        self.crash_data = None

        #Read configuration
        self._config_load()

        self.builder.get_object("filechooserbutton_application").select_filename(self._config_get("application", '(None)'))
        self.builder.get_object("filechooserbutton_normal").select_filename(self._config_get("normal", '(None)'))
        self.builder.get_object("filechooserbutton_crashing").select_filename(self._config_get("crash", '(None)'))
        self.builder.get_object("spinbutton_timeout").set_value(float(self._config_get("timeout",10)))


        if self._config_get("sendkeys.repeat","repeat") == "True":
            self.builder.get_object("radiobutton_repeat").set_active(True)
        else:
            self.builder.get_object("radiobutton_once").set_active(True)

        self.builder.get_object("spinbutton_sendkeys_timeout").set_value(float(self._config_get("sendkeys.timeout","2.0")))

        self.builder.get_object("checkbutton_keystrokes").set_active(self._config_get("sendkeys.enabled","True") == "True")
        
        self.builder.get_object("entry_sendkeys").set_text(self._config_get("sendkeys.keystrokes", "^{q}"))

        self.enable_sendkeys(self._config_get("sendkeys.enabled","True") == "True")

        self.builder.get_object("filechooserbutton_backup_folder").set_filename(self._config_get("backup.folder", "(None)"))
        self.builder.get_object("filechooserbutton_backup_folder").set_sensitive(self._config_get("backup.folder_enabled","False") == "True")

        self.running = False
        self.builder.get_object("button_cancel").set_sensitive(self.running)
        self.builder.get_object("button_reduce").set_sensitive(not self.running)
        self.worker = None

        self.message("Wellcome!")
        #Get the Main Window, and show it!
        self.builder.get_object("MainWindow").show()


if __name__ == "__main__":
    gtk.gdk.threads_init()
    rcf = RCFGtk()
    gtk.main()
