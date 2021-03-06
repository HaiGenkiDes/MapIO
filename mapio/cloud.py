#!/usr/bin/env python

#python 3 compatibility
from __future__ import print_function

#third party imports
import numpy as np

from .dataset import DataSet,DataSetException
from .gridbase import Grid
from openquake.hazardlib.geo import geodetic



class Cloud(DataSet):
    def __init__(self,lon,lat,data):
        if lon.shape != lat.shape or lon.shape != data.shape or lat.shape != data.shape:
            raise DataSetException('Input lat/lon/data arrays must have same shape.')
        self._lon = lon
        self._lat = lat
        self._data = data

    def getData(self):
        return self._data

    def setData(self,data):
        if data.shape != self._lon.shape:
            raise DataSetException('Cloud.setData() input data must match dimensions of lat/lon')
        self._data = data

    def getBounds(self):
        return (self._lon.min(),self._lon.max(),self._lat.min(),self._lat.max())

    def trim(self,bounds):
        inside = (self._lon > bounds[0]) & (self._lon < bounds[1]) & (self._lat > bounds[2]) & (self._lat < bounds[3])
        self._lon = self._lon[inside]
        self._lat = self._lat[inside]
        self._data = self._data[inside]

    def getValue(self,lat,lon,method='nearest'):
        if method == 'nearest':
            d = geodetic.distance(lon,lat,self._lons,self._lats)
            imin = d.argmin()
            return self._data[imin]
        else:
            raise NotImplementedError('Only nearest neighbor method implemented at this time.')

    def interpolateToGrid(self,geodict,method='linear'):
        raise NotImplementedError('interpolateToGrid not implemented yet for the Cloud class.')
