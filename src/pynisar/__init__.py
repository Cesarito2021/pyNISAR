"""Independent NISAR L-band SAR research software."""
from .products import inspect_product as inspect, read_window as read
from .analysis import analyze_product as process
from .nisar import plot_halpha, plot_haalpha, plot_htheta
from .product_plots import plot_product as plot, write_product_study as report
from .decompositions import decompose
from .remote import open_remote
from .samples import sample, process_sample

__version__ = '0.1.0a1'
__all__ = ['inspect', 'read', 'process', 'plot', 'report', 'plot_halpha',
           'plot_haalpha', 'plot_htheta', 'decompose', 'open_remote',
           'sample', 'process_sample']
