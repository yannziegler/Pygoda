# Configuration file for the Sphinx documentation builder.

# import pygoda

# -- Project information
project = 'Pygoda'
copyright = 'MMXXII, <a href="https://yannziegler.com">Yann Ziegler</a>'
author = 'Yann Ziegler'

release = '0.1' # pygoda.__version__
version = '0.1.0' # pygoda.__version__

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'alabaster'

# -- Options for EPUB output
epub_show_urls = 'footnote'
