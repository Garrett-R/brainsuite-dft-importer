BrainSuite dft importer
=======================

This script takes a .dft file exported from BrainSuite and imports it into Blender with each tract being a separate object.

NOTE: this is an unofficial script not written by the BrainSuite developers.  If you have any issues please let me know! 

Usage
-----

First you must have generated tracts in BrainSuite.  If you don't know how to use BrainSuite, you can download it and follow the tutorials [here](http://www.brainsuite.org).  Once the tracts are generated, go to File -> Save Fiber Tracts -> Save Full Set (or Save Subset).  This will save out a .dft file.

Open up Blender, then copy and paste the contents of brainsuite_dft_importer.py into Blender's text editor.  Edit the parameters which appear at the top of the file.  For example, the first one is called dft_file and is the absolute path to the .dft file you'd like imported.  The parameters are documented in the script itself.
