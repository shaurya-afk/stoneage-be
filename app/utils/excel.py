from pathlib import Path
import pandas as pd
from uuid import uuid4

class ExcelGenerator:
    def __init__(self, output_dir:str = "generated_excel"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_excel(self, data: dict | list) -> Path:
        file_name = f"extraction_{uuid4().hex[:8]}.xlsx"
        file_path = self.output_dir / file_name

        if isinstance(data, list) and data and isinstance(data[0], dict):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data])
        df.to_excel(file_path, index=False)

        return file_path