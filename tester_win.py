# This program implement a debugging loop of a program
# The process run to acomplish a crash in the process, a timed out or the normal exit process.
# Only depends of ctypes and a set of definitions in defines.py
#Based in:
#http://msdn.microsoft.com/en-us/library/windows/desktop/ms681675(v=vs.85).aspx
#
# _*_coding:utf8_*_

'''
This is a tester! 
'''

from  ctypes import *
from defines import *
from time import time, sleep
import sys

#save & restore registers
import subprocess
#temporary files
import hashlib, os,tempfile
#Backup important files
import tarfile
#Timer Class
import threading, win32com.client, pythoncom, win32api

kernel32 = windll.kernel32

global pids 
pids = None

def sendKeyStrokes(keystroke_string):
    ''' This will try to send keystrokes to the debugees '''
    global pids
    try:
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
        shell = win32com.client.Dispatch("WScript.Shell")
        print "trying to send keys to pids:%s"%pids
        for pid in pids:
            if shell.AppActivate(pid):
                print "Keys(%s) sent to pid: %d"%(keystroke_string, pid)
                win32api.Sleep(100)
                win32api.Sleep(100)
        shell.SendKeys(keystroke_string)
    except Exception, E:
        print E

class RepeatTimer(threading.Thread):
    '''Stolen class that implements a self repeating timer'''
    def __init__(self, interval, function, iterations=0, args=[], kwargs={}):
        threading.Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.iterations = iterations
        self.args = args
        self.kwargs = kwargs
        self.finished = threading.Event()
    
    def run(self):
        count = 0
        while not self.finished.is_set() and (self.iterations <= 0 or count < self.iterations):
            self.finished.wait(self.interval)
            if not self.finished.is_set():
                self.function(*self.args, **self.kwargs)
                count += 1
    def cancel(self):
        self.finished.set()

def delFilesIn(d=[]):
    ret = True
    try:
        for root, dirs, files in os.walk(d):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))
    except Exception, E:
        print E
        ret = False
    return ret

def saveRegisters(keys):
    print '[X]Saving registers...'
    ret = None
    try:
        cmd = [r'c:\windows\system32\reg.exe', 'EXPORT']
        for rootKey in keys:
            #OJO SI EL NOMBRE DE LA CLAVE TIENE GUIONES
            tmp =  [rootKey ,  r'c:\bkp\\' + rootKey.replace('\\','-') + '.reg', '/y']
            ret = subprocess.call( cmd + tmp )
        print '[X] registers saved'
    except Exception, E:
        print E
    return ret      
        
def restoreRegisters(keys):
    print '[X]Restoring registers...'    
    cmd = [r'c:\windows\system32\reg.exe', 'IMPORT']
    ret = None
    try:
        for rootKey in keys:
            tmp = [r'c:\bkp\%s.reg' % rootKey.replace('\\','-')] 
            ret = subprocess.call( cmd + tmp )
    except Exception, E:
        print E, repr(cmd+tmp)
    print '[X]Restored registers...'
    return ret

def backup(d,bkpDir='c:\users\w7\Desktop', bkpName='crazy-bkp.tar.gz'):
    ret = True
    try:
        tar = tarfile.open(bkpDir+bkp_name,'w:gz')
        tar.add(d)
        tar.close()
    except Exception, E:
        print E
        ret = False    
    return ret

def restore(f,drive=r'c:\\'):
    ret = True
    try:
        tar = tarfile.open(f,'r:gz')
        tar.extractall(drive)
    except Exception, E:
        print E
        ret = False        
    return ret

def test(cmd, data64, extension,  timeout=10, keystrokes = [], bkpFiles = [],regKeys=[]):
    assert timeout > 0 and len(data64)>=0 and (extension=='' or extension[0]=='.')

    cmd = ' '.join(cmd)
    if data64:
        tempfilename = tempfile.NamedTemporaryFile(suffix=extension,delete=False).name
        data = data64.decode('base64')
        file(tempfilename,"wb").write(data)
        print "Temporary file md5: <%s>"%hashlib.md5(data).hexdigest()
        print "Temporary filename: %s"%tempfilename
        data64 = None
    else:
        tempfilename = ''
    
    saveRegisters(regKeys)
    #Backup some important files
    backups = []
    for fn in bkpFiles:
        newname = 'bkp-'+os.path.basename(fn)+'.tar.gz'
        if not backup(fn, bkpName=newname):
            print "Backup ERROR"
        backups.append(newname)
        print 'Backup %s in Desktop'%fn
        
    #Setting up the virtual keystrokes repeating timer
    timers = []
    for sendkeys_timeout, repeate, sendkeys in keystrokes:
        sendkeys = sendkeys.replace("$TESTFILE",tempfilename)
        print "Setting up the virtual keystrokes repeating timer to %d"%sendkeys_timeout
        keys = RepeatTimer(sendkeys_timeout,sendKeyStrokes, args= [sendkeys])
        timers.append(keys)

    for keys in timers:
        print repr(keys)
        keys.start()

    #ipdb.set_trace()
    print repr(cmd)
    try:
        closed = run(cmd.replace('$TESTFILE',tempfilename), timeout)    
    except Exception , E:
        print 'Exception running:', E

    #UNSetting the virtual keystrokes repeating timer
    for keys in timers:
        keys.cancel()

    #Remove files recently created in Important directories at test time
    for fn in bkpFiles:
            delFilesin(fn)

    #Restore files previously saved.    
    for fn in backups:
        restore(r'c:\users\w7\Desktop\\'+fn)
        print 'Restored %s'%('f')

    #Restore the windows registers
    restoreRegisters(regKeys)

    sleep(1)
    return closed

def run(cmd, timeout = 10):
    global pids
    print "running:", cmd

    pi = ProcessInfo()
    si = StartupInfo()

    #Running cmd in a new process 
    #http://msdn.microsoft.com/en-us/library/windows/desktop/ms682425(v=vs.85).aspx
    success = kernel32.CreateProcessA(c_char_p(0),  #cmd must not be None
                                      c_char_p(cmd),
                                      0,
                                      0,
                                      0,
                                      1,            #follow forks 
                                      0,
                                      0,
                                      byref(si),
                                      byref(pi))

    if not success:
        print "[*] Process \"%s\" failed  " % cmd
        print kernel32.GetLastError()
        exit(-1)

    pids = None
    closed = "Normal"
    maxTime = time() + timeout

    dwContinueStatus = DBG_CONTINUE
    debug = DEBUG_EVENT()

    while pids is None or pids:

        #Wait for a debugging event to occur. The second parameter indicates
        #that the function does not return until a debugging event occurs. 
        if kernel32.WaitForDebugEvent(byref(debug), 100):
            #Process the debugging event code.
            if debug.dwDebugEventCode == EXCEPTION_DEBUG_EVENT:
                #Process the exception code. When handling 
                #exceptions, remember to set the continuation 
                #status parameter (dwContinueStatus). This value 
                #is used by the ContinueDebugEvent function. 
                if debug.u.Exception.ExceptionRecord.ExceptionCode in [EXCEPTION_ACCESS_VIOLATION, 
                                                                       EXCEPTION_ARRAY_BOUNDS_EXCEEDED,
                                                                       EXCEPTION_DATATYPE_MISALIGNMENT,
                                                                       EXCEPTION_ILLEGAL_INSTRUCTION,
                                                                       EXCEPTION_IN_PAGE_ERROR,
                                                                       EXCEPTION_PRIV_INSTRUCTION,
                                                                       EXCEPTION_STACK_OVERFLOW] :
                    print 'EXCEPTION CODE:', hex(debug.u.Exception.ExceptionRecord.ExceptionCode)
                    closed  = 'Crashed'
                else:
                    #print 'CODE:', hex(debug.u.Exception.ExceptionRecord.ExceptionCode)
                    dwContinueStatus = DBG_EXCEPTION_NOT_HANDLED
                             
            elif debug.dwDebugEventCode == CREATE_PROCESS_DEBUG_EVENT:
                if pids is None:
                    pids = []
                pids.append(debug.dwProcessId)               
            elif debug.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT:
                pids.remove(debug.dwProcessId)
              
        #If crashed or the timeout was reached
        #Close all processes in the debugge loop.    
        if maxTime < time() or closed == 'Crashed':
            if closed != 'Crashed':
                closed = 'Timeout'
            #http://msdn.microsoft.com/en-us/library/windows/desktop/ms686714(v=vs.85).aspx
            for pid in reversed(pids):
                handle = kernel32.OpenProcess(1, 0, pid)
                kernel32.TerminateProcess(handle,0)
                kernel32.CloseHandle(handle)
        #print repr(pids)    
        #http://msdn.microsoft.com/en-us/library/windows/desktop/ms679285(v=vs.85).aspx 
        kernel32.ContinueDebugEvent(debug.dwProcessId, debug.dwThreadId, dwContinueStatus)

    return closed
##################################################################################################

if __name__ == '__main__':

    if len(sys.argv) < 2:
        print 'Usage: python tester.py "command_line" '

    #cmd = [r'c:\Program Files\Adobe\Reader 10.0\Reader\AcroRd32.exe']
    #cmd = [r'c:\windows\system32\calc.exe']
    cmd = ['c:\users\w7\desktop\crash_test.exe SPAWN SPAWN TIMEOUT']
    #crashf = r'x:\acroread\crashed-48309707.pdf'
    #normalf = r'x:\foxit\normal-47112630.pdf'        

    '''cmd = ['c:\Program Files (x86)\Microsoft Money Plus\MNYCoreFiles\msmoney.exe', '$TESTFILE']
    crashf = r'c:\Users\w7\Desktop\minimal-792diff.mny'
    normalf = r'c:\Users\w7\Desktop\normal-46591027.mny'
    
    regKeys=['HKCU\Software\Classes\VirtualStore',
         'HKCU\Software\Microsoft\FTP',
         'HKCU\Software\Microsoft\Investor',
         'HKCU\Software\Microsoft\Money',
         'HKCU\Software\Microsoft\Windows',
         'HKCU\Software\Microsoft\Windows Script',]
    
    normal64 = file(normalf, 'rb').read().encode('base64')
    crash64 = file(crashf, 'rb').read().encode('base64')

    
    closed = test(cmd, normal64, '.mny', 5 , [], [], regKeys)
    print 'closed:',closed
    closed = test(cmd, crash64, '.mny', 30 , [(5,1,"^q"), (5,1,"^q")], [], regKeys)
    print 'closed:',closed
    '''
    closed = test(cmd, "", '', 10, [], [], [])
