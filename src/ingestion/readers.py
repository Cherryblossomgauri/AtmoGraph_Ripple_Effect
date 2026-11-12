"""Read the validated CSV dataset with pandas."""
from pathlib import Path
import pandas as pd
FILES=["countries","industries","transactions","ports","shipping_routes","industry_port_links","disruptions"]
def read_dataset(folder="data/synthetic"):
    root=Path(folder)
    return {name:pd.read_csv(root/f"{name}.csv") for name in FILES}
