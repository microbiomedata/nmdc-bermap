from pathlib import Path
from .nmdc_sfas_brcs import *

THIS_PATH = Path(__file__).parent

SCHEMA_DIRECTORY = THIS_PATH.parent / "schema"
MAIN_SCHEMA_PATH = SCHEMA_DIRECTORY / "nmdc_sfas_brcs.yaml"
