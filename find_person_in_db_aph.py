# modifying find_person_in_db from TEI_parser for APH
import re
from normality import normalize

# import from appended path
import parliament.models as pm
import cities.models as cmodels
from django.db.models import Q

def find_person_in_db_aph(name, add_info={}, create=True, verbosity=1):

    if name is None:
        print("! Warning: no valid name string given")
        if create:
            person, created = pm.Person.objects.get_or_create(surname='Error: no valid string', first_name='')
            return person
        else:
            return None

    original_string = name

    if 'pp' in add_info.keys():
        pp = add_info['pp']
    else:
        pp = None

    if 'date' in add_info.keys():
        date = add_info['date']

    name = re.sub(r'\([^)]*\)', '', name)
    name = name.replace('  ', ' ')
    name = name.replace('Dr ', '')
    name = name.replace('Mrs ', '')
    name = name.replace('Ms ', '')
    name = name.replace('Mr ', '')
    name = name.replace('The ', '')

    if len(name.split(' ')) > 1:
        surname = name.split(' ')[-1]
        firstname = name.split(' ')[0]
    else:
        surname = name
        firstname = ''

    if "nameid" in add_info.keys():
        name_id = add_info['nameid']
    else:
        name_id = None

    if verbosity > 1:
        print("Finding speaker with name id: {}".format(name_id))
    #! search using person.position ?
    #! could be important if speaker holds ministerial position
    # position = PERSON_POSITION.search(name)
    if "role" in add_info.keys():
        position = add_info["role"]
    else:
        position = None

        if position and verbosity > 1:
            print("= position: {}".format(position.group(0)))

    # find matching entry in database
    # provision for Speaker of Parliament
    if name_id != '10000' and name_id != '110000' and name_id != '1000':
        if verbosity > 1:
            print("Finding speaker from MP database...")
        query = pm.Person.objects.filter(aph_id=name_id)

        if len(query) == 1:
            return query.first()

        else:
            print("Duplicate name ID entries detected")
            return query.first()

    elif name_id == '10000' or name_id == '110000' or name_id == "1000":
        if verbosity > 1:
            print("Finding speaker from Speaker database...")
        # check for name to see if speaker or deputy
        if surname == "SPEAKER":
            postquery = pm.Post.objects.get(
            title='Speaker',
            parlperiod__n=pp,
            start_date__lte = date,
            end_date__gte = date
            )

            parl_speaker = postquery.person
            return parl_speaker

        else:
            rquery = pm.Post.objects.filter(
            Q(title='Deputy Speaker') | Q(title='Second Deputy Speaker'),
            parlperiod__n=pp,
            start_date__lte = date,
            end_date__gte = date
            )

            if len(rquery) == 1:
                parl_speaker = rquery.first().person
                return parl_speaker

            elif len(rquery) > 1:
                squery = rquery.filter(person__surname = surname)

                if len(squery) == 1:
                    parl_speaker = squery.first().person
                    return parl_speaker

                elif len(squery) == 0:
                    print("Person not found in database as speaker: {}".format(name))
                    print("Trying to find person by name")

                    tquery = pm.Person.objects.filter(surname=surname, alt_first_names__contains=[firstname])
                    if len(tquery) == 1:
                        print("Found speaker by name: {}".format(name))
                        return tquery.first()

            else:
                print("Person not found in database: {}".format(name))


    # if query returns no results
    else:
        print("Person not found in database: {}".format(name))

        if verbosity > 0:
            print("name: {}".format(name))
            print("first name: {}, surname: {}".format(firstname, surname))
            print("name id: {}".format(name_id))

        if create:
            person = pm.Person(surname=surname, first_name=firstname)

            if name_id != 10000 and not None:
                person.aph_id = name_id

            if 'session' in add_info.keys():
                session_str = "{sn:03d}".format(sn=add_info['session'])
            else:
                session_str = "???"

            if 'source_type' in add_info.keys():
                source_str = add_info['source_type']
            else:
                source_str = ""

            person.in_parlperiod = [pp]
            person.active_country = cmodels.Country.objects.get(name='Australia')

            person.save()

            #seat, created = pm.Seat.objects.get_or_create(
            #parlperiod=pm.ParlPeriod.objects.get(n=pp),
            #occupant=person
            #)

            #if electorate:
            #    constituency, created = pm.Constituency.objects.get_or_create(
            #    parliament = pm.Parl.objects.get(country=cmodels.Country.objects.get(name="Australia")),
            #    name=electorate)
            #    constituency.save()
            #    seat.constituency = constituency

            #seat.save()

            print("Created person: {}".format(person))
            return person

        else:
            return None

# copied from normdatei.text
def clean_text(text):

    text = text.replace('\r', '\n')
    text = text.replace(u'\xa0', ' ')
    text = text.replace(u'\x96', '-')
    text = text.replace(u'\xad', '-')
    text = text.replace(u'\u2014', '–')
    # text = text.replace(u'\u2013', '–')
    return text
