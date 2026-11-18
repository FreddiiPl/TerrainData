import numpy as np

from scipy.interpolate import griddata
from pyproj import Geod

import cartopy.crs as ccrs
import cartopy.feature as cfeature

import matplotlib.pyplot as plt
import matplotlib        as mpl
from matplotlib.patches import Circle
mpl.rcParams['axes.linewidth'] = 1.2
mpl.rcParams['xtick.direction'] = 'in'
mpl.rcParams['ytick.direction'] = 'in'
mpl.rcParams['xtick.top'] = False
mpl.rcParams['ytick.right'] = False
mpl.rcParams['xtick.minor.visible'] = False
mpl.rcParams['ytick.minor.visible'] = False
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

        
    

    def plot_grid(self,nr_points=100, savefig=None):
        lon_min = self.lon.min()
        lon_max = self.lon.max()
        lat_min = self.lat.min()
        lat_max = self.lat.max()
        lo_grid = np.linspace(lon_min, lon_max, nr_points)
        la_grid = np.linspace(lat_min, lat_max, nr_points)
        
        lo, la = np.meshgrid(
            lo_grid, la_grid
        )
        
        h = griddata(
            (self.lon, self.lat),
            self.height,
            (lo, la),
            method = "linear"
        )
        
        fig = plt.figure(figsize=(12,8))
        ax  = plt.axes(projection=ccrs.PlateCarree())

        cf = ax.contourf(
            lo,
            la,
            h,
            levels=100,
            cmap="magma",
            transform=ccrs.PlateCarree()
        )
        
        cs = ax.contour(
            lo, la, h,
            levels=np.arange(
                np.nanmin(h),
                np.nanmax(h),
                100
            ),
            colors="k",
            linewidths=0.5,
            alpha=0.3
        )

        gl = ax.gridlines(
            draw_labels=True,
            linestyle=":",
            alpha=0.1
                    )
        
        gl.top_labels = False
        gl.right_labels = False
        
        ax.clabel(cs, fmt="%d m", fontsize=8)
        
        ax.set_title(
            "Terrain Elevation Map - Kebnekaise (Lantmäteriet 1m source)",
            fontsize=14,
            pad=15,
            fontweight="bold"
        )

                
        ax.set_xlim(lon_min, lon_max)
        ax.set_ylim(lat_min, lat_max)
        
        
        ax.set_aspect("auto")
        plt.colorbar(cf, ax=ax, label="Height [m]"),
        plt.tight_layout()
        plt.show()
        if savefig is not None:
            fig.savefig(f"./figures/{savefig}", dpi=300)
    
    
    def plot_hexbin(self, savefig=None):
        fig = plt.figure(figsize=(12, 8))
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.add_feature(
            cfeature.LAND,
            facecolor="lightgray"
        )
        
        hb = ax.hexbin(
            self.lon,
            self.lat,
            C=self.height,
            gridsize=500,
            cmap="magma",
            transform=ccrs.PlateCarree(),
        )
        
        self.add_compass_rose(ax=ax)
        
        plt.colorbar(hb, ax=ax, label="Height [m]")

        plt.tight_layout()
        plt.show()
        
        if savefig is not None:
            fig.savefig(f"./figures/{savefig}", dpi=300)
        

    def plot_profile(self,):
        fig, ax = plt.subplots(figsize=(12,8))
        ax.plot(self.distance, self.height_profile)
        ax.set_xlabel("distance [km]")
        ax.set_ylabel("height [m]")

        plt.tight_layout()
        plt.show()

    
    @staticmethod
    def add_compass_rose(ax, x=0.9, y=0.1, size=0.05):
        # Outer circle
        circle = Circle(
            (x, y),
            size,
            transform=ax.transAxes,
            fill=False,
            lw=1.5,
            color="black",
            zorder=100
        )
        ax.add_patch(circle)

        # Cardinal directions
        ax.text(x, y + size * 1.4, "N",
                transform=ax.transAxes,
                ha="center", va="center",
                fontsize=12, fontweight="bold")

        ax.text(x, y - size * 1.4, "S",
                transform=ax.transAxes,
                ha="center", va="center")

        ax.text(x + size * 1.4, y, "E",
                transform=ax.transAxes,
                ha="center", va="center")

        ax.text(x - size * 1.4, y, "W",
                transform=ax.transAxes,
                ha="center", va="center")

        # Main north arrow
        ax.annotate(
            "",
            xy=(x, y + size * 0.8),
            xytext=(x, y - size * 0.8),
            xycoords=ax.transAxes,
            arrowprops=dict(
                arrowstyle="-|>",
                lw=2,
                color="black"
            ),
            zorder=101
        )

        # East-West line
        ax.plot(
            [x - size * 0.8, x + size * 0.8],
            [y, y],
            transform=ax.transAxes,
            color="black",
            lw=1,
            zorder=101
        )
