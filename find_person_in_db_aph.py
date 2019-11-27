# modifying find_person_in_db from TEI_parser for APH

def find_person_in_db_aph(name, add_info={}, create=True,
                      first_entry_for_unresolved_ambiguity=True, verbosity=1):

    #if name.strip('-– ()') is '' or name is None:
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

    #! search using person.position ?
    #! could be important if speaker holds ministerial position
    # position = PERSON_POSITION.search(name)
    if "role" in add_info.keys():
        # if position:
        #    if add_info["position"] != position:
        #        print("! Warning: position does not match ({}, {})".format(
        #            position, add_info["position"]))
        position = add_info["role"]
    else:
        position = None

        if position and verbosity > 1:
            print("= position: {}".format(position.group(0)))

    #title = TITLE.match(cname)
    #if title:
    #    title = title.group(0)
    #cname = TITLE.sub('', cname).strip()

    if "party" in add_info.keys() and not 'N/A':
        party = add_info['party']
        p_party, created = pm.Party.objects.get_or_create(name=party)
    else:
        party = None

    if "electorate" in add_info.keys():
        electorate = add_info['electorate']
    else:
        electorate = None

    # find matching entry in database
    # provision for Speaker of Parliament
    if name_id != '10000':
        query = pm.Person.objects.filter(name_id=name_id)

    elif name_id == '10000':
        postquery = pm.Post.objects.get(
        parlperiod__n=pp,
        start_date__lte = date,
        end_date__gte = date
        )

        parl_speaker = postquery.person
        name_id = parl_speaker.name_id
        return parl_speaker

    if len(query) == 1:
        return query.first()

    elif len(query) > 1:
        if party:
            rquery = query.filter(party__alt_names__contains=[party])
            if len(rquery) == 1:
                return emit_person(rquery.first(), period=pp, party=party)
            elif len(rquery) > 1:
                query = rquery

        if pp:
            rquery = query.filter(in_parlperiod__contains=[pp])
            if len(rquery) == 1:
                return emit_person(rquery.first(), period=pp, party=party)
            elif len(rquery) > 1:
                query = rquery

        print("! Warning: Could not distinguish between persons!")
        print("For name string: {}".format(name))
        print("first name: {}, surname: {}".format(firstname, surname))
        print("Query: {}".format(query))

        if first_entry_for_unresolved_ambiguity:
            print('Taking first entry of ambiguous results')
            return query.first()
        else:
            return None

    # if query returns no results
    else:
        print("Person not found in database: {}".format(name))

        if verbosity > 0:
            print("name: {}".format(name))
            print("first name: {}, surname: {}".format(firstname, surname))

        if create:
            person = pm.Person(surname=surname, first_name=firstname)

            #if title:
            #    person.title = title

            if party:
                try:
                    party_obj = pm.Party.objects.get(name=party)
                    person.party = party_obj

                except pm.Party.DoesNotExist:
                    print("! Warning: party could not be identified: {}".format(party))

            if position:
                person.positions = [position]
                # use position with data model "Post" ?

            if name_id != 10000 and not None:
                person.name_id = name_id

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

            seat, created = pm.Seat.objects.get_or_create(
            parlperiod=pm.ParlPeriod.objects.get(n=pp),
            occupant=person
            )

            if electorate:
                constituency, created = pm.Constituency.objects.get_or_create(
                parliament=pm.Parl.objects.get(country=cmodels.Country.objects.get(name="Australia")),
                name=electorate
                )
                constituency.save()
                seat.constituency = constituency

            seat.save()

            print("Created person: {}".format(person))
            return person

        else:
            return None
