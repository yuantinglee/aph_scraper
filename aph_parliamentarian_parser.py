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
        #if mdb.tag == "VERSION":
        #    continue
        #names = mdb.find('NAMEN')
        #biodata = mdb.find('BIOGRAFISCHE_ANGABEN')
        pol = df_all.loc[i]

        person = Person(
            surname=pol['surname'],
            first_name=pol['firstName'],
            unique_id=pol['uniqueID']
            )
###########
        person.title = names[-1].find('ANREDE_TITEL').text
        person.academic_title = names[-1].find('AKAD_TITEL').text
        ortszusatz = names[-1].find('ORTSZUSATZ').text
        if ortszusatz is not None:
            person.ortszusatz = ortszusatz.strip('() ')

        person.adel = names[-1].find('ADEL').text

        surnames_list = []
        firstnames_list = []

        for name in names:
            surname = name.find('NACHNAME').text

            if isinstance(surname, str):
                surnames_list.append(surname)

                if len(surname.split(' ')) > 1:
                    surnames_list.append(surname.split(" ")[-1])

            firstname = name.find('VORNAME').text

            if isinstance(firstname, str):
                firstnames_list.append(firstname)

                if len(firstname.split(' ')) > 1:
                    for fname in firstname.split(" "):
                        if len(fname) > 2:
                            firstnames_list.append(fname)

        person.alt_surnames = list(set(surnames_list))
        person.alt_first_names = list(set(firstnames_list))

        if verbosity > 0:
            # print name
            if person.adel is None:
                print("Person: {}".format(person))
            else:
                print("Person: {} {}".format(person.adel, person))

        person.year_of_birth=person.dob.year

        person.date_of_death = german_date(biodata.find('STERBEDATUM').text)
        if biodata.find('GESCHLECHT').text == "männlich":
            person.gender = Person.MALE
        elif biodata.find('GESCHLECHT').text == "weiblich":
            person.gender = Person.FEMALE
        else:
            print(biodata.find('GESCHLECHT').text)
        #person.family_status = biodata.find('FAMILIENSTAND').text
        #person.religion = biodata.find('RELIGION').text
        person.occupation = biodata.find('BERUF').text
        person.short_bio = biodata.find('VITA_KURZ').text

        try:
            person.party = Party.objects.get(alt_names__contains=[biodata.find('PARTEI_KURZ').text])
        except Party.DoesNotExist:
            if biodata.find('PARTEI_KURZ').text == 'Plos':
                person.party = Party.objects.get(name="parteilos")
                pass
            else:
                print("Warning: Party not found: {}".format(biodata.find("PARTEI_KURZ").text))
                warn += 1

        person.active_country = Country.objects.get(name='Australia')
        person.positions = ['parliamentarian']
        person.information_source = "AustralianPoliticians"
        person.save()


        wp_list = []

        # loop over wahlperioden
        for wp in mdb.findall('WAHLPERIODEN/WAHLPERIODE'):

            wp_list.append(int(wp.find('WP').text))

            # do not use seats of the Volkskammer
            if wp.find('MANDATSART').text == "Volkskammer":
                continue

            pp, created = ParlPeriod.objects.get_or_create(
                parliament=parl,
                n=wp.find('WP').text
                )

            seat, created = Seat.objects.get_or_create(
                parlperiod=pp,
                occupant=person
                )
            seat.start_date = german_date(wp.find('MDBWP_VON').text)
            seat.end_date = german_date(wp.find('MDBWP_BIS').text)

            # loop over institutions
            for ins in wp.findall('INSTITUTIONEN/INSTITUTION'):

                if ins.find('INSART_LANG').text == 'Fraktion/Gruppe':

                    try:
                        party = Party.objects.get(
                                alt_names__contains=[ins.find('INS_LANG').text]
                                )
                    except Party.DoesNotExist:
                        if ins.find('INS_LANG').text == "Fraktionslos":
                            person.party = Party.objects.get(name="fraktionslos")
                            pass

                        else:
                            print("Warning: Party not found: {}".format(ins.find('INS_LANG').text))
                            warn += 1

                else:
                    if verbosity > 0:
                        print("Other institution: {}".format(ins.find('INS_LANG').text))

            if wp.find('MANDATSART').text == "Direktwahl":
                seat.seat_type = Seat.DIRECT
                direct_region = wp.find('WKR_LAND').text
                try:
                    wk, created = Constituency.objects.get_or_create(
                        parliament=parl,
                        number=wp.find('WKR_NUMMER').text,
                        name=wp.find('WKR_NAME').text,
                        region=Region.objects.get(name=LANDS[direct_region])
                        )
                    wk.save()
                    seat.constituency = wk
                    seat.save()
                except KeyError:
                    print("Warning: Region of Direktmandat not found: {}".format(direct_region))
                    warn += 1
                except Region.DoesNotExist:
                    print("Warning: Region of Direktmandat not in regions: {}".format(direct_region))
                    warn += 1

            elif wp.find('MANDATSART').text == "Landesliste":
                seat.seat_type = Seat.LIST
                list_region = wp.find('LISTE').text
                try:
                    pl, created = PartyList.objects.get_or_create(
                        parlperiod=pp,
                        region=Region.objects.get(name=LANDS[list_region])
                        )
                    seat.list = pl
                    seat.save()
                    pl.save()
                except KeyError:
                    print("Warning: Region of Landesliste not found: {}".format(list_region))
                    warn += 1
                except Region.DoesNotExist:
                    print("Warning: Region of Landesliste not in regions: {}".format(list_region))
                    warn += 1

            else:
                print("Warning: Unknown Mandatsart: {}".format(wp.find('MANDATSART').text))

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
        Person.objects.filter(information_source="MDB Stammdata").delete()

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
