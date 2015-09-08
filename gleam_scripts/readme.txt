Repository for scripts used in generating the extra-galactic GLEAM source catalogue, including:

 # Running the Phase 1 pipeline (http://mwa-lfd.haystack.mit.edu/twiki/bin/view/Main/GLEAM_Phase1)
 # Running the Phase 2 pipeline (http://mwa-lfd.haystack.mit.edu/twiki/bin/view/Main/GLEAM_Phase2)
 # Making catalogues from images including
  # Correcting YY mosaics to match XX mosaics
  # Fitting polynomials to the combined mosaics and fits to SEDs of sources from NVSS, MRC and VLSSr
  # Applying the polynomicals to rescale the mosaics
  # Combining the mosaics in the overlap regions
  # loads of source-finding

- The super-computer submission scripts can be found in bin/ ; copy this whole directory to your $HOME
- The templates on which they act can be found in queue/ ; copy this whole directory to your $HOME
- The other useful scripts can be found in scripts/ ; you will probably want to copy the contents of this directory into your bin/ directory, as you'll need many of them to run the pipelines.
- Some catalogues are also in MWA_Tools/catalogues ; you don't need to do anything with these, as long as $MWA_CODE_BASE is set, they will automatically be found.
- bsm_v1.txt is the 'bright source model' catalogue used for peeling bright sources. If you want to use it, put it in your project directory (one level below an observation directory).

