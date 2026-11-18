import requests
import os
import polars as pl

from pathlib import Path

from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm


script_dir = Path(__file__).resolve().parent
credentials_path = script_dir / "credentials.env"

class Lantmateriet:

    url = "https://api.lantmateriet.se/stac-hojd/v1"


    def __init__(self,
                south=None,
                north=None,
                west=None,
                east=None,):
        
        self.south = south
        self.north = north
        self.west = west
        self.east = east

        self.username = os.getenv("lantmateriet_username")
        self.password = os.getenv("lantmateriet_password")

        self.session = requests.Session()
        self.session.auth = (
            self.username,
            self.password,
        )
    
        
    def collections(self):
        r = requests.get(f"{self.url}/collections")
        r.raise_for_status()

        data = r.json()
        df = pl.from_dicts(data["collections"])

        print(df["id"])
    

    def search(self, limit=100):
        payload = {
            "collections": ["dtm-cog"], # this is the dem id
            "bbox": [self.west, self.south, self.east, self.north],
            "limit": limit
        }

        r = requests.post(
            f"{self.url}/search",
            json=payload
        )
        r.raise_for_status()

        data = r.json()
        df = pl.DataFrame(
            [
                {
                    "id": feature["id"],
                    "collection": feature["collection"],
                    "bbox": feature.get("bbox"),
                    "datetime": feature["properties"].get("datetime"),
                    "href": feature["assets"]["data"]["href"],
                }
                for feature in data["features"]
            ]
        )

        return df
    

    def download(self, row):
        
        url = row["href"]

        filename = Path(url).name
        filepath = self.cache_dir / filename

        if not filepath.exists():
            print("Fetching response...")
            r = self.session.get(url, stream=True)
            r.raise_for_status()

            total_bytes = int(r.headers.get("content-length", 0))
            chunk_size = 1024 * 1024
            with open(filepath, "wb") as f:
                with tqdm(
                    total=total_bytes,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc="Downloading Elevation Data"
                ) as pbar:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
        
        
        return filepath


    def download_parallel(self,workers=1):
        df = self.search()
        print(df)
        print(f"Downloading in total {df.shape[0]} tiles")

        self._cache()
        with ThreadPoolExecutor(max_workers=workers) as executor:

            filepaths = list(
                executor.map(
                    self.download,
                    df.iter_rows(named=True)
                )
            )
        
        print("Finished!")
        return filepaths

    def _cache(self,dir=None):
        if dir is None:
            dir = os.environ.get("CACHE_DIR", "./cache_directory/Lantmateriet")
            
        
        self.cache_dir = Path(dir).expanduser().resolve().absolute()
        
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)



