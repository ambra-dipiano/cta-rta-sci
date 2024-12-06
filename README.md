### **Environment** **

To create a virtual environment with all required dependencies:

```bash
conda env create --name <envname> --file=environment.yaml
```

Note that you should already have anaconda installed: https://www.anaconda.com/

## **rtasci**
All code is found in this directory, you can setup the source code as follows:

```bash
python setup.py develop
```

**Sub-directories:**

- cfg -> configuration class and configuration files
- lib -> classes
- misc -> miscellaneous scripts
- pipelines -> pipelines with different tools and techniques
- timing -> scripts to compare tools and techniques

### **Calibration database**

To complete the environment be sure to download and install the correct IRFs (only prod2 comes with ctools installation). Public ones can be found here: https://www.cta-observatory.org/science/cta-performance/

### **Configuration file**

Under cfg you can find an example of configuration file. Description of each parameter is commented within. This file will serve as input when running the code.

### **CALDB degradation**
Be sure to have your calibration database installed under $CTOOLS/share. You can pass a single CALDB or a list, the degraded version will placed along side the nominal one. It will have the same suffix, replacing "prod" with "degr" (i.e., prod2 --> degr2).

```bash
python degradation_caldb.py --caldb prod3b pro3b-v2
```

Note: currently the code simply halves the affective area (and consequently renormalise the background rates).

## rtasci
To extract spectra and lightcurves from the templates (one, a list or the entire sample):

```bash
python prepareGRBcatalog.py -f cfg/config.yaml
```

To run the simulation:

```bash
python simGRBcatalog.py -f cfg/config.yaml
```

To perform the analysis:

```bash
python pipeline/pipeline_name.py -f cfg/config.yaml
```
You are required to substitute pipeline_name.py with the chosen script (currently only one pipeline is available but there will be more in the future).

All steps above may be run together with the following:

```bash
python rtapipe.py -f cfg/config.yaml
```
This will first extract all data specified in the configuration file, then simulate the entire sample, finally it will analyse each simulation. Files will be removed (by default) after the simulation so be sure to have enough space to store them. It will avoid running multiple simulation of the same sample if, i.e., you want to perform different types of analysis on it.

To simulate a single run you can alternatively use

```bash
python simGRB.py -f cfg/config.yaml
```

To simulate a wobble observation (only crab simulations are currently allowed) you can use:

```bash
python simWobble.py -f cfg/config.yaml
```

<HR>
[**] subsceptible to changes


### Branch power9

This branch will enable the usage of this software on a machine with the POWER9 architecture.

* Some dependencies were removed from the yaml requirements file due to missing anaconda packages for this architecture.
* ctools - anaconda package not found - it must be installed from sources.
* healpy - anaconda package found, but it downloads a lot of required packages that can create conflicts.
* xml - anaconda package not found - but it's not used.
* pyregion - anaconda package not found - install it with pip.
* Healpy import in RTAUtils is removed.

This branch will also pull the "leodev" branch commits.
