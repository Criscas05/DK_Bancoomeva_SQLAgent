import os
import sys
import json
import pandas as pd
import pdb
from pathlib import Path


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.knowledge_base import create_knowledge_base

def main(index_name: str = "index_sqlagent", path_data: str = ""):
    global knowledge_base
    knowledge_base = pd.read_excel(path_data)
    # pdb.set_trace()
    create_knowledge_base(index_name, knowledge_base)


if __name__ == '__main__':

    script_location = Path(__file__).resolve()
    project_root = script_location.parent.parent.parent

    index_name = "index_sqlagent"
    path_data = project_root / "data" / "Ejemplosquerys.xlsx"

    main(index_name, path_data)

