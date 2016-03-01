#!/usr/bin/env python

#python 3 compatibility
from __future__ import print_function
import os.path
import sys

#stdlib imports
import abc
import textwrap
import glob
import os

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
mapiodir = os.path.abspath(os.path.join(homedir,'..'))
sys.path.insert(0,mapiodir) #put this at the front of the system path, ignoring any installed mapio stuff


#third party imports
from mapio.gridbase import Grid
from mapio.grid2d import Grid2D
from mapio.dataset import DataSetException
from mapio.geodict import GeoDict
import numpy as np
from scipy import interpolate
import shapely
from affine import Affine
from rasterio import features
from shapely.geometry import MultiPoint,Polygon,mapping
        
def test_basics():
    geodict = GeoDict({'xmin':0.5,'xmax':3.5,'ymin':0.5,'ymax':3.5,'dx':1.0,'dy':1.0,'ny':4,'nx':4})
    data = np.arange(0,16).reshape(4,4)
    grid = Grid2D(data,geodict)
    print('Testing basic Grid2D functionality (retrieving data, lat/lon to pixel coordinates, etc...')
    np.testing.assert_almost_equal(grid.getData(),data)

    assert grid.getGeoDict() == geodict

    assert grid.getBounds() == (geodict.xmin,geodict.xmax,geodict.ymin,geodict.ymax)
    
    lat,lon = grid.getLatLon(0,0)

    assert lat == 3.5 and lon == 0.5
        
    row,col = grid.getRowCol(lat,lon)

    assert row == 0 and col == 0
    
    value = grid.getValue(lat,lon)

    assert value == 0
    
    frow,fcol = grid.getRowCol(1.0,3.0,returnFloat=True)

    assert frow == 2.5 and fcol == 2.5
    
    irow,icol = grid.getRowCol(1.0,3.0,returnFloat=False)

    assert irow == 2 and icol == 2

    #test getting values in and outside of the grid bounds
    lat = np.array([0.0,0.5,2.5,4.0])
    lon = np.array([0.0,0.5,2.5,4.0])
    default = np.nan
    output = np.array([np.nan,12,6,np.nan])
    value = grid.getValue(lat,lon,default=default)

    np.testing.assert_almost_equal(value,output)
    
    print('Passed basic Grid2D functionality (retrieving data, lat/lon to pixel coordinates, etc...')
    
def test_cut():
    geodict = GeoDict({'xmin':0.5,'xmax':4.5,'ymin':0.5,'ymax':4.5,'dx':1.0,'dy':1.0,'ny':5,'nx':5})
    data = np.arange(0,25).reshape(5,5)

    print('Testing data extraction...')
    grid = Grid2D(data,geodict)
    xmin,xmax,ymin,ymax = (2.5,3.5,2.5,3.5)
    newgrid = grid.cut(xmin,xmax,ymin,ymax)
    output = np.array([[7,8],[12,13]])
    np.testing.assert_almost_equal(newgrid.getData(),output)
    print('Passed data extraction...')

    print('Testing data trimming with resampling...')
    #make a more complicated test using getboundswithin
    data = np.arange(0,84).reshape(7,12)
    geodict = GeoDict({'xmin':-180,'xmax':150,
                       'ymin':-90,'ymax':90,
                       'dx':30,'dy':30,
                       'nx':12,'ny':7})
    grid = Grid2D(data,geodict)
    sampledict = GeoDict.createDictFromBox(-75,45,-45,75,geodict.dx,geodict.dy)
    cutdict = geodict.getBoundsWithin(sampledict)
    newgrid = grid.cut(cutdict.xmin,cutdict.xmax,cutdict.ymin,cutdict.ymax)
    output = np.array([[16,17,18,19],
                       [28,29,30,31],
                       [40,41,42,43],
                       [52,53,54,55]])
    np.testing.assert_almost_equal(newgrid.getData(),output)
    print('Passed data trimming with resampling...')

def test_interpolate():
    geodict = GeoDict({'xmin':0.5,'xmax':6.5,'ymin':1.5,'ymax':6.5,'dx':1.0,'dy':1.0,'ny':6,'nx':7})
    data = np.arange(14,56).reshape(6,7)
    
    for method in ['nearest','linear','cubic']:
        print('Testing interpolate with method "%s"...' % method)
        grid = Grid2D(data,geodict)
        sampledict = GeoDict({'xmin':3.0,'xmax':4.0,
                              'ymin':3.0,'ymax':4.0,
                              'dx':1.0,'dy':1.0,
                              'ny':2,'nx':2})
        grid.interpolateToGrid(sampledict,method=method)
        if method == 'nearest':
            output = np.array([[30.0,31.0],[37.0,38.0]])
        elif method == 'linear':
            output = np.array([[34.,35.],[41.,42.]])
        elif method == 'cubic':
            output = np.array([[34.,35.],[41.,42.]])
        else:
            pass
        np.testing.assert_almost_equal(grid.getData(),output)
        print('Passed interpolate with method "%s".' % method)

def test_rasterize():
    geodict = GeoDict({'xmin':0.5,'xmax':3.5,
                       'ymin':0.5,'ymax':3.5,
                       'dx':1.0,'dy':1.0,
                       'ny':4,'nx':4})
    print('Testing rasterizeFromGeometry() burning in values from a polygon sequence...')
    #Define two simple polygons and assign them to shapes
    poly1 = [(0.25,3.75),(1.25,3.25),(1.25,2.25)]
    poly2 = [(2.25,3.75),(3.25,3.75),(3.75,2.75),(3.75,1.50),(3.25,0.75),(2.25,2.25)]
    shape1 = {'properties':{'value':5},'geometry':mapping(Polygon(poly1))}
    shape2 = {'properties':{'value':7},'geometry':mapping(Polygon(poly2))}
    shapes = [shape1,shape2]
    print('Testing burning in values where polygons need not contain pixel centers...')
    grid = Grid2D.rasterizeFromGeometry(shapes,geodict,fillValue=0,attribute='value',mustContainCenter=False)
    output = np.array([[5,5,7,7],
                       [5,5,7,7],
                       [0,0,7,7],
                       [0,0,0,7]])
    np.testing.assert_almost_equal(grid.getData(),output)
    print('Passed burning in values where polygons need not contain pixel centers.')

    print('Testing burning in values where polygons must contain pixel centers...')
    grid2 = Grid2D.rasterizeFromGeometry(shapes,geodict,fillValue=0,attribute='value',mustContainCenter=True)
    output = np.array([[5,0,7,0],
                       [0,0,7,7],
                       [0,0,0,7],
                       [0,0,0,0]])
    np.testing.assert_almost_equal(grid2.getData(),output)
    print('Passed burning in values where polygons must contain pixel centers.')


def test_copy():
    data = np.arange(0,16).astype(np.float32).reshape(4,4)
    geodict = GeoDict({'xmin':0.5,'xmax':3.5,'ymin':0.5,'ymax':3.5,'dx':1.0,'dy':1.0,'ny':4,'nx':4})
    grid1 = Grid2D(data,geodict)
    grid2 = grid1.copyFromGrid(grid1)
    grid1._data[0,0] = np.nan
    print(grid2._data)
    print(grid2._geodict)

def test_setData():
    data = np.arange(0,16).astype(np.float32).reshape(4,4)
    geodict = GeoDict({'xmin':0.5,'xmax':3.5,'ymin':0.5,'ymax':3.5,'dx':1.0,'dy':1.0,'ny':4,'nx':4})
    grid1 = Grid2D(data,geodict)
    x = np.ones((4,4))
    try:
        grid1.setData(x) #this should pass
        print('setData test passed.')
    except DataSetException as dse:
        print('setData test failed.')
    try:
        x = np.ones((5,5))
        grid1.setData(x)
        print('setData test did not fail when it should have.')
    except DataSetException as dse:
        print('setData test failed as expected.')

    try:
        x = 'fred'
        grid1.setData(x)
        print('setData test did not fail when it should have.')
    except DataSetException as dse:
        print('setData test failed as expected.')
    
    
if __name__ == '__main__':
    test_rasterize()
    test_interpolate()
    test_basics()
    test_cut()
    test_copy()
    test_setData()
        