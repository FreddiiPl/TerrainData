import os
from source.DEM.OpenTopography import OpenTopography


class copernicusDEM(OpenTopography):

    valid_demtype = {"COP30", "COP90"}

    def __init__(self,
                south=None,
                north=None,
                west=None,
                east=None,
                demtype="COP30"):
        
        self.south = south
        self.north = north
        self.west = west
        self.east = east

        if demtype not in self.valid_demtype:
            raise ValueError(
                f"{demtype} is not a valid type! Only supporting {self.valid_demtype}"
                )


        self.dir = os.environ.get("CACHE_DIR", f"./cache_directory/{demtype}")
        super().__init__(
            demtype=demtype,
            south=south,
            north=north,
            west=west,
            east=east,
            outputFormat="GTiff",
            dataserver="global",
            dir=self.dir
        )




        

