import re
from regular_expressions_aph import *
import pandas as pd
from datetime import datetime

import django
import platform

if platform.node() == "srv-mcc-apsis":
    sys.path.append('/home/leey/tmv/BasicBrowser/')
    data_dir = '/home/leey/AustralianPoliticians/data-raw/'

else:
    # local paths
    sys.path.append('/home/leey/Documents/Data/tmv/BasicBrowser/')
    data_dir = '/home/leey/Documents/Data/AustralianPoliticians/data-raw/'

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

# import from appended path
import parliament.models as pm
import cities.models as cmodels
from utils import *

# --------------------------------------------
# define parl
parl, created = pm.Parl.objects.get_or_create(
    country=cmodels.Country.objects.get(name="Australia"),
    level='N'
)

if __name__ == '__main__':
    parlperiods = pd.read_csv('./data_files/APH_parlperiod.csv')
    parlperiods_past = parlperiods[:-1]
    add_parlperiod(parlperiods_past, parl)
