import os
import sys
import re
import pandas as pd
from datetime import datetime

import django
import parliament.models as pm
import cities.models as cmodels

# --------------------------------------------

def add_parlperiod(df, parl):
    """Parses parliamentary periods from list to database"""
    for index, row in df.iterrows():
        n = index+1

        pp, created = pm.ParlPeriod.objects.get_or_create(
        parliament = parl,
        n = n
        )

        start_date = datetime.strptime(row['Elected'].strip(), '%d.%m.%Y')
        end_date = datetime.strptime(row['Dissolved'].strip(), '%d.%m.%Y')

        pp.start_date = start_date
        pp.end_date = end_date

        n_years = end_date.year - start_date.year
        years = []
        years.append(start_date.year)
        if n_years > 0:
            for i in range(1, n_years):
                years.append(start_date.year+i)
        years.append(end_date.year)

        pp.years = years
        pp.save()


def add_speaker(df, role):
    """Parses House Speakers from list to database"""
    # modify to add deputy speakers as well by including variable role?

    for i in df.index:
        entry = df.loc[i]
        surname = entry['Last_Name']
        first_name = entry['First_Name']
        middle_name = entry['Middle_Names']

        pquery = pm.Person.objects.filter(
        surname = surname,
        alt_first_names__contains = [first_name],
        information_source = "AustralianPoliticians"
        )

        if len(pquery) == 1:
            person = pquery[0]

        elif len(pquery) > 1:
            rquery = pquery.filter(alt_first_names__contains=[middle_name])
            if len(rquery) == 1:
                person = rquery[0]
            else:
                print("Politician not found for name: {} {}".format(first_name, surname))
                continue

        #### Dates
        start_date = datetime.strptime(str(entry['Start_Date']).strip(), '%d.%m.%Y')
        end_date = datetime.strptime(str(entry['End_Date']).strip(), '%d.%m.%Y')

        n_years = end_date.year - start_date.year
        years = []
        years.append(start_date.year)
        if n_years > 0:
            for i in range(1, n_years):
                years.append(start_date.year+i)
        years.append(end_date.year)

        #### Find parlperiod
        pp = pm.ParlPeriod.objects.get(
        parliament = parl,
        start_date__lte = start_date,
        end_date__gte = end_date
        )

        post, created = pm.Post.objects.get_or_create(
        person = person,
        title = role,
        parlperiod = pp,
        years = years,
        start_date = start_date,
        end_date = end_date
        )

        post.save()

    print("Done")

def parse_aph_data(file, verbosity=0):
    """Adds parliamentarians from AustralianPoliticians dataset to database"""
    warn = 0

    df_pol = pd.read_csv(file)
    print("read data from {}".format(file))

    # going through entries for mdbs
    for i in df_pol.index:
        pol = df_pol.loc[i]

        person = pm.Person(
            surname=str(pol['surname']),
            first_name=str(pol['firstName']),
            unique_id=str(pol['uniqueID']),
            aph_id=str(pol['aphID'])
            )

        # profile information
        title = pol['title']
        if pd.isnull(title) == False:
            person.title = str(title)

        dob = pol['birthDate']
        dod = pol['deathDate']

        if pd.isnull(pol['birthYear']) == False:
            yob = int(pol['birthYear'])

        if pd.isnull(dob) == False:
            person.date_of_birth = datetime.strptime(str(dob), '%Y-%m-%d')
        else:
            person.year_of_birth = yob

        if pd.isnull(dod) == False:
            person.date_of_death = datetime.strptime(str(dod), '%Y-%m-%d')

        if pol['gender'] == "male":
            person.gender = pm.Person.MALE
        elif pol['gender'] == "female":
            person.gender = pm.Person.FEMALE

        # additional names
        firstnames_list = []

        firstname = pol['allOtherNames']

        if isinstance(firstname, str):
            firstnames_list.append(firstname)

            if len(firstname.split(' ')) > 1:
                for fname in firstname.split(" "):
                    if len(fname) > 2:
                        firstnames_list.append(fname)


        commonname = pol['commonName']

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

        person.active_country = cmodels.Country.objects.get(name='Australia')
        # adding positions
        if pol['member'] == 1:
            person.positions = ['Member']
        if pol['senator'] == 1:
            person.positions = ['Senator']

        person.information_source = "AustralianPoliticians2"
        person.save()

    print("Done. {} warnings.".format(warn))


def add_parties(file, verbosity=1):
    """Add parties of parliamentarians to database"""

    df_par = pd.read_csv(file)
    print("read data from {}".format(file))

    parliament = pm.Parl.objects.get(country = cmodels.Country.objects.get(name='Australia'))

    for i in df_par.index:
        pol = df_par.loc[i]

        unique_id = str(pol['uniqueID'])
        person = pm.Person.objects.get(unique_id=unique_id)

        if verbosity > 0:
            print("Adding party for {}".format(unique_id))

        # party and party membership info
        party_abbrev = str(pol['partyAbbrev'])
        party_name = str(pol['partyName'])
        party_simplified = str(pol['partySimplifiedName'])

        party_alt_names = [party_abbrev, party_simplified]

        # get Party object
        par_party, created = pm.Party.objects.get_or_create(
            name=party_name,
            alt_names = party_alt_names,
            parliament = parliament
        )

        party_from = pol['partyFrom']
        party_to = pol['partyTo']

        # create PartyMembership association
        par_mem = pm.PartyMembership(
            person=person,
            party=par_party
        )

        if pd.isnull(party_from) == False or pd.isnull(party_to) == False:
            par_mem.period_unknown = False

            if pd.isnull(party_from) == False:
                par_mem.entry_date = datetime.strptime(str(party_from), '%Y-%m-%d')
            if pd.isnull(party_to) == False:
                par_mem.resignation_date = datetime.strptime(str(party_to), '%Y-%m-%d')

        par_mem.save()

    print("Done.")
