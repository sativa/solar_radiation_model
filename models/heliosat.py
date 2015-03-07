#!/usr/bin/env python

import numpy as np
from datetime import datetime, timedelta
import glob
import os
from netcdf import netcdf as nc
from cache import Cache, Loader
from helpers import to_datetime, short, show

from core import cuda_can_help
if cuda_can_help:
    import gpu as geo
else:
    import cpu as geo
# import processgroundstations as pgs



class Heliosat2(object):

    def __init__(self, filenames):
        self.filenames = filenames
        self.SAT_LON = -75.113  # -75.3305 # longitude of sub-satellite point in degrees
        self.IMAGE_PER_HOUR = 2
        self.GOES_OBSERVED_ALBEDO_CALIBRATION = 1.89544 * (10 ** (-3))
        self.i0met = np.pi / self.GOES_OBSERVED_ALBEDO_CALIBRATION
        self.cache = TemporalCache(self)

    def process_temporalcache(self, loader, cache):
        geo.process_temporalcache(self, loader, cache)

    def process_globalradiation(self, loader, cache):
        geo.process_globalradiation(self, loader, cache)

    def process_validate(self, root):
        from libs.statistics import error
        estimated = nc.getvar(root, 'globalradiation')
        measured = nc.getvar(root, 'measurements')
        stations = [0]
        for s in stations:
            show("==========\n")
            show("Station %i (%i slots)" % (s,  measured[:, s, 0].size))
            show("----------")
            show("mean (measured):\t", error.ghi_mean(measured, s))
            show("mean (estimated):\t", estimated[:, s, 0].mean())
            ghi_ratio = error.ghi_ratio(measured, s)
            bias = error.bias(estimated, measured, s)
            show("BIAS:\t%.5f\t( %.5f %%)" % (bias, bias * ghi_ratio))
            rmse = error.rmse_es(estimated, measured, s)
            show("RMSE:\t%.5f\t( %.5f %%)" % (rmse, rmse * ghi_ratio))
            mae = error.mae(estimated, measured, s)
            show("MAE:\t%.5f\t( %.5f %%)" % (mae, mae * ghi_ratio))
            show("----------\n")
            error.rmse(root, s)

    def run_with(self, loader):
        self.process_globalradiation(loader, self.cache)
        #    process_validate(root)
        # draw.getpng(draw.matrixtogrey(data[15]),'prueba.png')


class TemporalCache(Cache):

    def __init__(self, strategy):
        super(TemporalCache, self).__init__()
        self.strategy = strategy
        self.filenames = self.strategy.filenames
        self.initialize_path(self.filenames)
        self.update_cache(self.filenames)
        self.cache = Loader(map(self.get_cached_file, self.filenames))
        self.root = self.cache.root

    def initialize_path(self, filenames):
        self.path = '/'.join(filenames[0].split('/')[0:-1])
        self.temporal_path = 'temporal_cache'
        self.index = {self.get_cached_file(v): v for v in filenames}
        if not os.path.exists(self.temporal_path):
            os.makedirs(self.temporal_path)

    def get_cached_file(self, filename):
        return '%s/%s' % (self.temporal_path, short(filename, None, None))

    def update_cache(self, filenames):
        self.clean_cache(filenames)
        self.extend_cache(filenames)

    def extend_cache(self, filenames):
        cached_files = glob.glob('%s/*.nc' % self.temporal_path)
        not_cached = filter(lambda f: self.get_cached_file(f) not in cached_files,
                            filenames)
        if not_cached:
            loader = Loader(not_cached)
            new_files = map(self.get_cached_file, not_cached)
            with nc.loader(new_files) as cache:
                self.strategy.process_temporalcache(loader, cache)

    def clean_cache(self, exceptions):
        cached_files = glob.glob('%s/*.nc' % self.temporal_path)
        old_cache = filter(lambda f: self.index[f] not in exceptions,
                           cached_files)

    def getvar(self, *args, **kwargs):
        name = args[0]
        if name not in self._attrs.keys():
            tmp = list(args)
            tmp.insert(0, self.cache.root)
            self._attrs[name] = nc.getvar(*tmp, **kwargs)
        return self._attrs[name]


def filter_filenames(filename):
    files = glob.glob(filename) if isinstance(filename, str) else filename
    last_dt = to_datetime(max(files))
    a_month_ago = (last_dt - timedelta(days=30)).date()
    include_lastmonth = lambda dt: dt.date() > a_month_ago
    files = filter(lambda f: include_lastmonth(to_datetime(f)), files)
    include_daylight = lambda dt: dt.hour - 4 >= 6 and dt.hour - 4 <= 18
    files = filter(lambda f: include_daylight(to_datetime(f)), files)
    return files


def workwith(filename="data/goes13.*.BAND_01.nc"):
    filenames = filter_filenames(filename)
    months = list(set(map(lambda dt: '%i/%i' % (dt.month, dt.year),
                          map(to_datetime, filenames))))
    show("=======================")
    show("Months: ", months)
    show("Dataset: ", len(filenames), " files.")
    show("-----------------------\n")
    loader = Loader(filenames)
    strategy = Heliosat2(filenames)
    strategy.run_with(loader)
    show("Process finished.\n")
