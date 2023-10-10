.. _howto:

How To
======

A mini how-to for Pygoda.
-------------------------

Pygoda interface is packed with many tooltips. You can get a lot of information on how to use Pygoda simply by hovering the different elements of its GUI.

Displaying the time series
~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Plot more/less stations:** go to menu Grid/Grid geometry
- **Plot another subset of stations (#1):** select another grid page in the combo on the left above the grid
- **Plot another subset of stations (#2):** click on one of the arrow next to the aforementioned combo
- **Plot another subset of stations (#3):** press ``LEFT`` (previous page) or ``RIGHT`` (next page) arrow while holding ``CTRL`` [grid must have focus]

Customising the subplots
~~~~~~~~~~~~~~~~~~~~~~~~

- **Adjust the time span:** tick ``t-sync`` and pick the starting and ending dates
- **Adjust the Y-axis range:** tick ``y-sync``, pick a reference level and bound type in corresponding combos (hover for tooltips), and set the lower and upper bounds

Computing time series characteristics (features), fitting models and sorting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Compute time series features and sorting:** select a parameter (aka feature) in the combo initially displaying 'Sorted by default order'
- **Display a feature while sorting with another one:** select the feature you want to display, then hold ``SHIFT`` and select the feature used for sorting *OR* select the feature used for sorting, then hold ``CTRL`` and select the feature you want to display (hover for tooltips)
- **Fit a model:** chose a model in the Fitted models group and pick one of the model parameter
- **Reverse the sort order:** tick or untick the 'Decreasing order' box

Selection
~~~~~~~~~

- **Select a station:** left click on a subplot or on a map
- **Select another station (#1):** left click on another station
- **Select another station (#2):** press ``LEFT`` (previous station) or ``RIGHT`` (next station) arrow
- **Select several stations:** left click while holding ``CTRL``
- **End selection:** right click on any subplot or anywhere on a map

Categories (default behaviour, can be configured)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **View another group of category (#1):** select another group in the top left combo
- **View another group of category (#2):** hold ``CTRL`` and press ``0``, ``1``, ...or ``9`` [category combo must have focus]
- **Set a station category (#1):** repeat left (next category) or right (previous category) click on a subplot while holding ``SHIFT``
- **Set a station category (#2):** select a subplot, then press ``+`` (next category) or ``-`` (previous category)
- **Set a station category (#3):** hover a subplot, then press ``1``, ``2``, ...or ``9`` (or ``0`` to assign no category); then the next station will be automatically selected [grid must have focus]
- **Toggle a station category:** press ``SPACE`` while hovering a subplot [grid must have focus]

Zoom plot
~~~~~~~~~

- **Snap crosshair to closest data point:** hover with mouse cursor (buggy for now!)
- **Snap crosshair to closest date:** hover while holding ``CTRL``
- **Snap crosshair to closest data value:** hover while holding ``SHIFT``
- **Compute basic statistics over an interval:** left click once to set the starting date and left click a second time to set the ending date; click one more time to reset

Cartopy map
~~~~~~~~~~~

- **Zoom in and out:** scroll over the map
- **Pan the map:** hold left click anywhere and pan
- **Set the reference point (used for sorting):** hold ``CTRL`` and middle click on the map at the location of your choice
- **Filter the stations by region (only when using an overlay):** middle click in the region of your choice

Leaflet map
~~~~~~~~~~~

- **Change the map layer:** pick another layer in the bottom-left menu
- **Plot a time series directly on the map:** right click on a station

Don't hesitate to explore Pygoda menus, docks and windows to find more functionalities!
