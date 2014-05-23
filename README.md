rcfast
======

This is supposed to be used after a crash is found via a trivial bitflipping fuzzing session. This expects a normal not crashing control file and a mutated same sized crashing  file. It will try to reduce the mutations on the crashing file checking that the resultant file still crashes on the configured application.
