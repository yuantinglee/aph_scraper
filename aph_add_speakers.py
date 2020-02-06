# coding: utf-8

import os
import re
import sys
from datetime import datetime
import pandas as pd

import django
import platform

if platform.node() == "srv-mcc-apsis":
    sys.path.append('/home/leey/tmv/BasicBrowser/')

else:
    # local paths
    sys.path.append('/home/leey/Documents/Data/tmv/BasicBrowser/')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

# import from appended path
import parliament.models as pm
import cities.models as cmodels
from django.contrib.auth.models import User
from aph_utils import *

# --------------------------------------------
parl, created = pm.Parl.objects.get_or_create(
    country=cmodels.Country.objects.get(name="Australia"),
    level='N'
)

# add speaker roles
if __name__ == '__main__':
    print("Adding speakers...")
    speakers = pd.read_csv('.data_files/APH_speakers.csv')
    speakers_past = speakers[:-1]
    add_speaker(speakers_past)
    print("Done.")

    print("Adding deputy speakers...")
    dep_speakers = pd.read_csv('.data_files/APH_deputy_speakers.csv')
    dep_speakers_past = dep_speakers[:-1]
    add_speaker(dep_speakers_past, role='Deputy Speaker')
    print("Done.")

    print("Adding second deputy speakers...")
    sec_dep_speakers = pd.read_csv('.data_files/APH_second_deputy_speakers.csv')
    add_speaker(sec_dep_speakers, role='Second Deputy Speaker')
    print("Done.")
