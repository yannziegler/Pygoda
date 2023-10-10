Installation of Pygoda
======================

First install
-------------

.. _install:

This software has been tested on recent GNU/Linux distributions (Debian, Archlinux) and Windows 10.
It has also been tested on a remote server (CentOS) using X forwarding through ssh to display the GUI on a Windows client.

To install the software on any platform, here is the recommended method:

#. Download and install the latest version of `miniconda <https://docs.conda.io/en/latest/miniconda.htm>`_ for your system.
#. Clone this repository using your preferred ``git`` tool. See the `GitHub documentation <https://docs.github.com/en/free-pro-team@latest/github/creating-cloning-and-archiving-repositories/cloning-a-repository>`_ if you have never done that before.
#. Create a new conda environment using the ``requirements.txt`` file located in the main Pygoda-beta folder. If necessary, you can check the corresponding section of the `conda documentation <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html>`_. Otherwise, go to the Pygoda-beta main folder, open a console and run:

    ::
    
       conda create -c conda-forge --file requirements.txt --name pygoda

    .. note::
    
       it is required to use the ``conda-forge`` channel as some packages are only available there for now.
   
   Please check that all the required packages have been installed without errors.
#. You're done! Now you can activate the newly created environment and launch Pygoda by running the ``pygoda.py`` file in the ``Pygoda-beta/pygoda`` folder (but please read the :ref:`Quickstart <quickstart>` section first). If you are not familiar with Python scripts and/or conda environments, please read the following paragraph before moving to the next section.

The ``pygoda`` environment created in step #3 must be activated whenever you want to use the software.
To do so, go to the ``Pygoda-beta/pygoda`` folder, open a console and run ``conda activate pygoda``.
Then, you can launch Pygoda with ``python pygoda.py``.
It is recommended to create an alias to avoid repeating these steps.
On Linux, you may add the following line to your ``.profile``, ``.bashrc`` or any other relevant config file for your shell:
::
    
    alias pygoda="cd /path/to/pygoda-installation-folder/Pygoda-beta/pygoda/ && conda activate pygoda && python pygoda.py"

Then, you can run Pygoda from anywhere with the command ``pygoda``.
On Windows, you should be able to do something similar with `doskey <https://docs.microsoft.com/en-us/windows/console/console-aliases>`_ (not tested yet).


Running
-------

.. _running:

To launch Pygoda, start an anaconda/miniconda console, then execute:
::

   conda activate pygoda
   cd "/path/to/pygoda-installation-folder/Pygoda-beta/pygoda/"
   python pygoda.py


Update
------

.. _updates:

To update Pygoda, go to Pygoda installation folder and run:
::

   git pull

or use your preferred GUI software for git.
