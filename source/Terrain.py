
import numpy as np

from scipy.interpolate import griddata
from pyproj import Geod

import cartopy.crs as ccrs
import cartopy.feature as cfeature

import matplotlib.pyplot as plt
import matplotlib        as mpl
mpl.rcParams['axes.linewidth'] = 1.2
mpl.rcParams['xtick.direction'] = 'in'
mpl.rcParams['ytick.direction'] = 'in'
mpl.rcParams['xtick.top'] = True
mpl.rcParams['ytick.right'] = True
mpl.rcParams['xtick.minor.visible'] = True
mpl.rcParams['ytick.minor.visible'] = True
mpl.rcParams['font.weight'] = 'bold'
mpl.rcParams['font.size'] = 12
mpl.rcParams['axes.labelweight'] = 'bold'


class Terrain:

    def __init__(
            self,
            data,
            region):

        self.data = data
        self.region = region
    

    @property
    def lon(self):
        return self.data.geometry.x.to_numpy()

    @property
    def lat(self):
        return self.data.geometry.y.to_numpy()

    @property
    def height(self):
        return self.data["height"].to_numpy()


    @property
    def geometry(self):
        return self.data.geometry

    @property
    def bounds(self):
        return self.data.total_bounds


    def profile(self,
                p1: tuple,
                p2: tuple,
                npts=1000):
        '''
        px - (lon, lat)
        '''

        # check if px is inside border

        lon_profile = np.linspace(p1[0], p2[0], npts)
        lat_profile = np.linspace(p1[1], p2[1], npts)
        self.height_profile = griddata(
            (self.lon, self.lat),
            self.height,
            (lon_profile, lat_profile),
            method="linear"
        )

        geod = Geod(ellps="WGS84")
        
        self.distance = np.zeros(npts)
        for idx in range(1, npts):

            _, _, ds = geod.inv(
                lon_profile[idx-1],
                lat_profile[idx-1],
                lon_profile[idx],
                lat_profile[idx]
            )

            # km
            self.distance[idx] = (
                self.distance[idx-1]
                + ds / 1000
            )

        return (self.distance, self.height_profile)


    def plot_grid(self,):
        fig = plt.figure(figsize=(12,8))
        ax  = plt.axes(projection=ccrs.PlateCarree())
        ax.add_feature(
            cfeature.LAND,
            facecolor="lightgray"
        )

        cf = ax.scatter(
            self.lon,
            self.lat,
            c=self.height,
            cmap="terrain",
            s=20,
            transform=ccrs.PlateCarree()
        )

        ax.gridlines(
            draw_labels=True,
            linestyle=":",
            alpha=0.5
                    )
        
        plt.colorbar(cf, ax=ax, shrink=0.71),
        plt.tight_layout()
        plt.show()
    

    def plot_profile(self,):
        fig, ax = plt.subplots(figsize=(12,8))
        ax.plot(self.distance, self.height_profile)
        ax.set_xlabel("distance [km]")
        ax.set_ylabel("height [m]")

        plt.tight_layout()
        plt.show()
