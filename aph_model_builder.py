import re
from regular_expressions_aph import *
import pandas as pd
from datetime import datetime

# import from appended path
import parliament.models as pm
import cities.models as cmodels

parl, created = pm.Parl.objects.get_or_create(
    country=cmodels.Country.objects.get(name="Australia"),
    level='N'
)

def add_parlperiod(df):
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

def add_speaker(df):
    """Parses House Speakers from list to database"""
    # modify to add deputy speakers as well by including variable role?

    for entry in df.itertuples():
        surname = entry.Last_Name
        first_name = entry.First_Name

        person, created = pm.Person.objects.get_or_create(
        surname = surname,
        first_name = first_name
        )
        #### Names
        #middle_names = []
        #for name in entry.Middle_Names:
        #    person.alt_first_names = middle_names.append(name)

        # person.name_id = '10000'
        if entry.Prefix != 'nan':
            person.title = entry.Prefix

        if entry.Title != 'nan':
            person.adel = entry.Title

        #### Parliamentary periods
        person.positions = ['Speaker']

        person.save()

        #### Dates
        start_date = datetime.strptime(entry.Start_Date.strip(), '%d.%m.%Y')
        end_date = datetime.strptime(entry.End_Date.strip(), '%d.%m.%Y')

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
        title = 'Speaker',
        parlperiod = pp,
        years = years,
        start_date = start_date,
        end_date = end_date
        )

        post.save()
