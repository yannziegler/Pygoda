# Pygoda

[![DOI](https://zenodo.org/badge/545984137.svg)](https://zenodo.org/badge/latestdoi/545984137)

A Python GUI to visualise and analyse efficiently large sets of geolocated time series.

Developed and maintained by Yann Ziegler @ [University of Bristol](https://www.bristol.ac.uk/) (UK), [School of Geographical Sciences](https://www.bristol.ac.uk/geography/), [Bristol Glaciology Centre](https://www.bristol.ac.uk/geography/research/bgc/)

This work is part of the [GlobalMass](https://www.globalmass.eu/) project.

> ✨ **Stay tuned!** Pygoda is being tested at the University of Bristol. The first official public release should be ready soon. In the meantime, you can follow Pygoda's development on the _develop_ branch here on GitHub. Please _watch_ this GitHub repository (top right button) to get a notification when Pygoda is available.

![Pygoda screenshot](pygoda/data/pygoda.png)

## Description

Pygoda is a standalone tool to visualise efficiently a large number of time series observed, recorded or computed at different locations on the Earth.

Thus, _Pygoda_ means any of the following, depending on your preference:
- **PY**thon for **G**e**O**reference**D** time series visualisation and **A**nalysis, or
- **Py**thon for **G**e**O**located **D**ata **A**nalysis, or my personal favourite
- **Py**thon for **G**e**O**located time series **D**i**A**gnosis

([yes, I know](http://phdcomics.com/comics/archive.php?comicid=1100))

Some examples of such geolocated data sets include:
- GPS positions at permanent or temporary stations,
- data from weather stations,
- river flow measurements,
- sea level at tide gauges,
- gravimetric measurements,
- ice flux at glaciers,
- air pollution data in cities,
- ...and really any georeferenced time series with any number of components.

## Documentation

Be sure to check [Pygoda's documentation](https://pygoda.readthedocs.io/en/latest/).

## Known major or annoying bugs

- Sometimes the labels don't close properly on Leaflet map: switch to a different grid page to resolve.
- When switching to a different group of categories, the update of the markers colour on the Leaflet map may fail: hover the subplots or map to resolve.
- It is not possible to zoom in past a certain level on Cartopy map with `lcc` projection (the maximum zoom level is hard-coded for now).

## Tools used

- Coding: Emacs with Spacemacs config
- Python packages: see requirements.txt
- PySide2 from Qt for the GUI
- Matplotlib and Cartopy for the default map
- pyqtgraph for high-speed plotting of the time series
- Leaflet for the online map

## Licence

This software is licensed under the [EUPL](LICENSE.md).

## Acknowledgements

Many thanks to all the current and future beta-testers!
