REDUCE CRASH FAST!!
===================

This is an humorous stunt of joshep@binamuse.com / @djoshep (most code from this guy!). Its main purpose was educational but it works well so it made it to github, enjoy. 

This is supposed to be used after a crash is found via a trivial bitflipping fuzzing session. 
This expects a normal not crashing control file and a mutated same sized crashing  file. It will try to reduce the mutations on the crashing file checking that the resultant file still crashes on the configured application.

It is based on the minimal debugging loop described here: http://blog.binamuse.com/2013/01/a-micro-windows-crash-catcher-in-python.html

Here there is the demo video:
And a spanish slidedeck here: http://bit.ly/1nbj9Lj

Pipy link: https://pypi.python.org/pypi/RCFast/0.1

Github: https://github.com/feliam/rcfast/
