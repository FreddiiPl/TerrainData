from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely import points
from shapely.geometry import box

from source.DEM.OpenTopography import OpenTopography
from source.Terrain import Terrain

import rasterio

class Region:

    DATA_PATH = (
        Path(__file__).resolve().parent /
        "Files/CNTR_RG_01M_2024_4326.gpkg"
    )

    def __init__(self, geometry):

        if isinstance(geometry, gpd.GeoSeries):

            self.geometry = gpd.GeoDataFrame(
                geometry=geometry,
                crs=geometry.crs
            )

        elif isinstance(geometry, gpd.GeoDataFrame):

            self.geometry = geometry

        else:
            raise TypeError(
                "geometry must be GeoSeries or GeoDataFrame"
            )

    @classmethod
    def from_country(cls, country):

        gdf = gpd.read_file(cls.DATA_PATH)

        match = gdf[
            gdf["NAME_ENGL"].str.lower()
            == country.lower()
        ]

        if match.empty:
            raise ValueError(
                f"Unknown country '{country}'"
            )

        return cls(match)
    
    @classmethod
    def from_bounds(
        cls,
        west,
        east,
        south,
        north,
        crs="EPSG:4326"
    ):

        bbox = gpd.GeoDataFrame(
            geometry=[
                box(
                    west,
                    south,
                    east,
                    north
                )
            ],
            crs=crs
        )

        return cls(bbox)
    

    @classmethod
    def from_geometry(
        cls,
        geometry,
        crs="EPSG:4326"
    ):

        gdf = gpd.GeoDataFrame(
            geometry=[geometry],
            crs=crs
        )

        return cls(gdf)

    @property
    def bounds(self):

        return self.geometry.total_bounds


    def generate_gridpoints(
        self,
        nr_points,
        epsg="EPSG:3035"
    ):

        region = self.geometry.to_crs(epsg)

        minx, miny, maxx, maxy = region.total_bounds

        x = np.linspace(
            minx,
            maxx,
            nr_points
        )

        y = np.linspace(
            miny,
            maxy,
            nr_points
        )

        xx, yy = np.meshgrid(x, y)

        pts = points(
            xx.ravel(),
            yy.ravel()
        )

        grid = gpd.GeoDataFrame(
            geometry=pts,
            crs=epsg
        )

        grid = gpd.sjoin(
            grid,
            region,
            predicate="within"
        )

        return grid
    

    def generate(
        self,
        nr_points,
        demtype="COP30",
        outputFormat="GTiff",
        dataserver="global"
    ):

        grid = self.generate_gridpoints(
            nr_points=nr_points
        )

        return self.fetch_dem_heights(
            grid,
            demtype=demtype,
            outputFormat=outputFormat,
            dataserver=dataserver
        )
    

    def fetch_dem_heights(self, data, demtype="COP30", outputFormat="GTiff", dataserver="global"):
        minx, miny, maxx, maxy = (
            data.to_crs("EPSG:4326")
            .total_bounds
        )
        
        topo = OpenTopography(demtype=demtype,
                              south=miny,
                              north=maxy,
                              west=minx,
                              east=maxx,
                              outputFormat=outputFormat,
                              dataserver=dataserver)
        
        filepaths = topo.download_recursive(south=miny,
                                            north=maxy,
                                            west=minx,
                                            east=maxx)
        
        terrain  = self.construct_heights(filepaths, data)
        
        return terrain

        
    def construct_heights(self, filepaths, grid):
            
            new_grid = grid.to_crs("EPSG:4326").copy()
            lons = new_grid.geometry.x.values
            lats = new_grid.geometry.y.values
            
            heights = np.full(len(new_grid), np.nan)
            
            for filepath in filepaths:
                nans_mask = np.isnan(heights)
                if not np.any(nans_mask):
                    break
                
                with rasterio.open(filepath) as src:
                    rows, cols = rasterio.transform.rowcol(src.transform, lons, lats)
                    rows = np.array(rows)
                    cols = np.array(cols)

                    valid_idx = (
                        (rows >= 0) & (rows < src.height) & 
                        (cols >= 0) & (cols < src.width) & 
                        nans_mask
                    )
                    
                    if not np.any(valid_idx):
                        continue
                    
                    band_data = src.read(1)
                    pixel_vals = band_data[rows[valid_idx], cols[valid_idx]]
                    
                    if src.nodata is not None:
                        is_valid_val = pixel_vals != src.nodata
                        final_idx = np.where(valid_idx)[0][is_valid_val]
                        heights[final_idx] = pixel_vals[is_valid_val]
                    else:
                        heights[valid_idx] = pixel_vals
                
            new_grid["height"] = heights
                    
            return Terrain(
                data=new_grid,
                region=self.geometry
            )