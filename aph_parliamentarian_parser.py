# coding: utf-8

# script for importing personal information from Australian members of parliament into the django parliament app
# uses data from the following source:
# https://github.com/RohanAlexander/AustralianPoliticians

import os
import lxml.etree as etree
import re
import sys
from datetime import datetime
import pandas as pd

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
from django.contrib.auth.models import User
from aph_utils import *

# --------------------------------------------

POL_FNAME = './data_files/aphid_parliamentarians.csv'
PAR_FNAME = data_dir + 'by_party.csv'

parl, created = pm.Parl.objects.get_or_create(
    country=cmodels.Country.objects.get(name="Australia"),
    level='N'
)

if __name__ == '__main__':
    delete_all = False
    delete_persons = False

    if delete_all:
        # to delete all existing entries for constituencies, partylists, seats and persons
        Constituency.objects.all().delete()
        PartyList.objects.all().delete()
        Party.objects.all().delete()
        Seat.objects.all().delete()
        Person.objects.all().delete()

    elif delete_persons:
        Person.objects.filter(information_source="AustralianPoliticians").delete()

    # parsing the data, adding members
    parse_aph_data(POL_FNAME)

    # adding parties of MPs
    add_parties(file=PAR_FNAME)
