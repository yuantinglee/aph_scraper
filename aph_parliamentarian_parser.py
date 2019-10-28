# coding: utf-8

# script for importing personal information from Australian members of parliament into the django parliament app
# uses data from the following source:
# https://github.com/RohanAlexander/AustralianPoliticians

from __future__ import print_function
import os, sys
import django
import re
import logging
import requests
import dataset
import datetime
from lxml import html
from urllib.parse import urljoin
# Extract agenda numbers not part of normdatei
from normality import normalize
import platform
import pandas as pd

import pprint

if platform.node() == "srv-mcc-apsis":
    sys.path.append('/home/leey/tmv/BasicBrowser/')
    data_dir = '/home/leey/AustralianPoliticians/data-raw/'
else:
    # local paths
    sys.path.append('/home/leey/Documents/Data/tmv/BasicBrowser/')
    data_dir = '/home/leey/Documents/Data/AustralianPoliticians/data-raw/'
    country_table_file = '/home/leey/Documents/Data/plpr-scraper/data/country_translations.csv'


# imports and settings for django and database
# --------------------------------------------

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from parliament.models import *
from cities.models import *

import xml.etree.ElementTree as ET

map_countries = True

#MDB_LINK = 'https://www.bundestag.de/resource/blob/472878/e207ab4b38c93187c6580fc186a95f38/MdB-Stammdaten-data.zip'
POL_FNAME = data_dir + 'all.csv'
PARTY_FNAME = data_dir + 'by_party.csv'


PARTY_NAMES = [
    {'name':'CP','alt_names':['Australian Country Party']},
    {'name': 'LIB', 'alt_names': ['Liberal Party of Australia']},
    {'name': 'NAT', 'alt_names': ['Nationalist Party']},
    {'name': 'ALP', 'alt_names': ['Australian Labor Party']},
    {'name': 'NCP', 'alt_names': ['National Country Party']},
    {'name': 'NPA', 'alt_names': ['National Party of Australia']}
    {'name': 'AD', 'alt_names': ['Australian Democrats']},
    {'name': 'ALP (N-C)', 'alt_names': ['Australian Labor Party (Non-Communist)']},
    {'name': 'NP', 'alt_names': ['The Nationals']},
    {'name': 'IND', 'alt_names': ['Independent']},
    {'name': 'ALP (A-C)', 'alt_names': ['Australian Labor Party (Anti-Communist)']},
    {'name': 'KAP', 'alt_names': ['Katters Australian Party']},
    {'name': 'PHON', 'alt_names': ['Pauline Hansons One Nation']},
    {'name': 'FLP', 'alt_names': ['Federal Labor Party']},
    {'name': 'ANTI-SOC', 'alt_names': ['Anti-Socialist Party']},
    {'name': 'UAP', 'alt_names': ['United Australia Party']},
    {'name': 'FT', 'alt_names': ['Free Trade']},
    {'name': 'GRN', 'alt_names': ['Australian Greens']},
    {'name': 'PROT', 'alt_names': ['Protectionist Party']},
    {'name': 'LANG LAB', 'alt_names': ['Lang Labor Party']},
    {'name': 'IND LAB', 'alt_names': ['Independent Labor']},
    {'name': 'CDP', 'alt_names': ['Christian Democratic Party']},
    {'name': 'DLP', 'alt_names': ['Democratic Labor Party']},
    {'name': 'QLP', 'alt_names': ['Queensland Labor Party']},
    {'name': 'LCL', 'alt_names': ['Liberal Country League']},
    {'name': 'GWA', 'alt_names': ['The Greens (WA) Inc']},
    {'name': 'NAT & FARMERS', 'alt_names': ['Nationalist and Farmers']},
    {'name': 'VFU', 'alt_names': ['Victorian Farmers Union']},
    {'name': 'IND LIB', 'alt_names': ['Independent Liberal']},
    {'name': 'NATS WA', 'alt_names': ['National Party of Australia (WA)']},
    {'name': 'FFP', 'alt_names': ['Family First Party']},
    {'name': 'TRP', 'alt_names': ['Tariff Reform Party']},
    {'name': 'CLP', 'alt_names': ['Country Liberal Party (Northern Territory)']},
    {'name': 'NDP', 'alt_names': ['Nuclear Disarmament Party']},
    {'name': 'IND PROT', 'alt_names': ['Independent Protectionist']},
    {'name': 'WAP', 'alt_names': ['Western Australia Party']},
    {'name': 'IND NAT', 'alt_names': ['Independent National(ist)']},
    {'name': 'PROG LAB', 'alt_names': ['Progressive Labor']},
    {'name': 'FU', 'alt_names': ['Farmers Union']},
    {'name': 'CA', 'alt_names': ['Centre Alliance']},
    {'name': 'NXT', 'alt_names': ['Nick Xenophon Team']},
    {'name': 'LM', 'alt_names': ['Liberal Movement']},
    {'name': 'NAT LIB', 'alt_names': ['National Liberal Party']},
    {'name': 'DHJP', 'alt_names': ['Derryn Hinchs Justice Party']},
    {'name': 'JLN', 'alt_names': ['Jacqui Lambie Network', 'Jacki Lambie Network']},
    {'name': 'PUP', 'alt_names': ['Palmer United Party']},
    {'name': 'APA', 'alt_names': ['Australian Progressive Alliance']},
    {'name': 'LDP', 'alt_names': ['Liberal Democratic Party']},
    {'name': 'REV TAR', 'alt_names': ['Revenue Tariff']},
    {'name': 'AMEP', 'alt_names': ['Australian Motoring Enthusiast Party']},
    {'name': 'FSU', 'alt_names': ['Farmers and Settlers Union']},
    {'name': 'ST CP', 'alt_names': ['State Country Party']},
    {'name': 'UCP', 'alt_names': ['United Country Party']},
    {'name': 'PP', 'alt_names': ['Progress Party']},
    {'name': 'UNITE AP', 'alt_names': ['Unite Australia Party (John Siddons Group)']},
    {'name': 'IND UAP', 'alt_names': ['Independent United Australia Party']},
    {'name': 'C PROG', 'alt_names': ['Country Progress Party']},
    {'name': 'AP', 'alt_names': ['Australia Party']},
    {'name': 'FCP', 'alt_names': ['Federal Country Party']},
]

parl, created = Parl.objects.get_or_create(
    country=Country.objects.get(name="Australia"),
    level='N'
)


def update_parties():
    for p in PARTY_NAMES:
        try:
            party = Party.objects.get(name=p['name'])
        except Party.DoesNotExist:
            party = Party(name=p['name'])

        party.alt_names = p['alt_names']
        party.save()


def fetch_mdb_data():
    if not os.path.exists(MDB_FNAME):
        print("fetching data from bundestag website")
        url = urlopen(MDB_LINK)
        zipfile = ZipFile(BytesIO(url.read()))
        zipfile.extractall("data/mdbs")
        print(zipfile.namelist())
    return


def german_date(str):
    if str is None:
        return None
    try:
        return datetime.datetime.strptime(str,"%d.%m.%Y").date()
    except ValueError:
        return datetime.datetime.strptime(str,"%Y").date()



def parse_mdb_data(verbosity=0):

    warn = 0

    df_pol = pd.read_csv(POL_FNAME)
    print("read data from {}".format(POL_FNAME))

    # going through entries for mdbs
    for i in df_pol.index:
        pol = df_pol.loc[i]

        person = Person(
            surname=pol['surname'],
            first_name=pol['firstName'],
            unique_id=pol['uniqueID']
            )

        # profile information
        title = pol['title']
        if title is not None:
            person.title = title

        person.year_of_birth = pol['birthYear']
        person.date_of_death = pol['deathDate']

        if pol['gender'] == "male":
            person.gender = Person.MALE
        else pol['gender'] == "female":
            person.gender = Person.FEMALE

        # additional names
        # surnames_list = []
        firstnames_list = []

        for name in pol['allOtherNames']:

            firstname = name

            if isinstance(firstname, str):
                firstnames_list.append(firstname)

                if len(firstname.split(' ')) > 1:
                    for fname in firstname.split(" "):
                        if len(fname) > 2:
                            firstnames_list.append(fname)

        for name in pol['commonName']:

            commonname = name

            if isinstance(commonname, str):
                firstnames_list.append(commonname)

                if len(commonname.split(' ')) > 1:
                    for cname in commonname.split(" "):
                        if len(cname) > 2:
                            firstnames_list.append(cname)

        person.alt_first_names = list(set(firstnames_list))

        if verbosity > 0:
            # print name
            print("Person: {}".format(person))

        # political party
        # match politician ID in df_pol to df_party to find party
        #try:
        #    person.party = Party.objects.get(alt_names__contains=)
        #except Party.DoesNotExist:
        #    if biodata.find('PARTEI_KURZ').text == 'Plos':
        #        person.party = Party.objects.get(name="parteilos")
        #        pass
        #    else:
        #        print("Warning: Party not found: {}".format(biodata.find("PARTEI_KURZ").text))
        #        warn += 1

        # name id


        person.active_country = Country.objects.get(name='Australia')
        # adding positions
        if pol['member'] == 1:
            person.positions = ['Member']
        if pol['senator'] == 1:
            person.positions = ['Senator']

        person.information_source = "AustralianPoliticians"
        person.save()

        person.in_parlperiod = wp_list
        person.save()

    print("Done. {} warnings.".format(warn))


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

    # getting the data
    fetch_mdb_data()
    # updating the parties
    update_parties()
    # parsing the data
    parse_mdb_data(verbosity=0)

    add_party_colors = True

    if add_party_colors:
        pcolours = [
            {'party':'cducsu','colour':'#000000'},
            {'party':'spd','colour':'#EB001F'},
            {'party':'linke','colour':'#8C3473'},
            {'party':'fdp','colour':'#FFED00'},
            {'party':'afd','colour':'#009EE0'},
            {'party':'gruene','colour':'#64A12D'},
        ]
        for pc in pcolours:
            p, created = Party.objects.get_or_create(name=pc['party'])
            p.colour = pc['colour']
            p.save()
