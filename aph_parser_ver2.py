#!/usr/bin/env python
# australian parliamentary protocol parser for xml_schema 2.2

import os
import lxml.etree as etree
import re
import sys
import datetime as dt
from datetime import datetime

import django
import platform

if platform.node() == "srv-mcc-apsis":
    sys.path.append('/home/leey/tmv/BasicBrowser/')
    xml_path = "/home/leey/australian_parliament_downloads/downloads_coal"

else:
    # local paths
    sys.path.append('/home/leey/Documents/Data/tmv/BasicBrowser/')
    xml_path = "/home/leey/Documents/Data/australian_parliament_downloads/downloads_coal"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

# import from appended path
import parliament.models as pm
import cities.models as cmodels
from django.contrib.auth.models import User
import tmv_app.models as tm

from find_person_in_db_aph import *
# ============================================================
# write output to file and terminal

import pprint
pretty_printer = pprint.PrettyPrinter(indent=4)

time_stamp = datetime.now().strftime("%y%m%d_%H%M%S")
output_file = "./parlsessions_aph_parser_output_" + time_stamp + ".log"
print("log file: {}".format(output_file))


class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open(output_file, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass

# ============================================================
class parse_xml_items(object):

    def __init__(self, xtree, v=1, period=None, session=None):
        self.v = v
        self.divs = xtree.findall("//chamber.xscript//debate")
        self.pp = int(xtree.xpath("//parliament.no//text()")[0])
        self.session = int(re.findall(r'\b\d+\b', xtree.xpath("//session.no//text()")[0])[0])

        if period is not None:
            if period != self.pp:
                print("! Warning: period number not matching: {} {}".format(period, self.pp))

        if session is not None:
            if session != self.session:
                print("! Warning: session number not matching: {} {}".format(session, self.session))

        self.date = datetime.strptime(xtree.xpath("//date//text()")[0], '%Y-%m-%d')

        if self.v > 0:
            print("xml with protocol {}/{} from {}".format(self.pp, self.session, self.date))

    def get_or_create_objects(self):

        replace_old_documents = False

        parl, created = pm.Parl.objects.get_or_create(
            country=cmodels.Country.objects.get(name="Australia"),
            level='N')
        if created and self.v > 0:
            print("created new object for parliament")

        pp, created = pm.ParlPeriod.objects.get_or_create(
            parliament=parl,
            n=self.pp)
        if created and self.v > 0:
            print("created new object for legislative period")

        if replace_old_documents == True:
            doc, created = pm.Document.objects.get_or_create(
                parlperiod=pp,
                doc_type="Parliamentary Debate",
                date=self.date
            )
            if created:
                print("created new object for parliamentary debate")
        else:
            doc = pm.Document(
                parlperiod=pp,
                doc_type="Parliamentary Debate",
                date=self.date
            )

        doc.sitting = self.session
        #doc.text_source = "GermaParlTEI from " + self.original_source
        doc.save()

        # delete old utterances associated with the doc
        doc.utterance_set.all().delete()
        self.doc = doc
        return doc

    def create_paragraph(self, text, utterance):
        text = text.replace("\n\n", "\n")
        text = clean_text(text)
        para = pm.Paragraph(
            utterance=utterance,
            text=text,
            word_count=len(text.split()),
            char_len=len(text)
        )
        para.save()
        return para

    def add_interjection(self, text, speaker, paragraph):
        interjection = pm.Interjection(
                paragraph=paragraph,
                text=text
                )
        interjection.type = pm.Interjection.SPEECH
        interjection.save()

        if speaker:
            interjection.persons.add(speaker)

    def run(self):

        self.get_or_create_objects()
        accepted_tags = ['speech', 'question', 'answer']

        ### start parsing of speeches
        for div in self.divs:
            if self.v > 1:
                print("div type: {}".format(div.xpath("type/text()")))

            for uts in div.iter('talk.start'):
                if uts.getparent().tag in accepted_tags:
                    # get agenda item
                    tops = uts.xpath('ancestor::debate/child::debateinfo/child::title/text()')[0]
                    tops = str(tops)

                    # create agenda item
                    agenda_item, created = pm.AgendaItem.objects.get_or_create(
                    title = tops,
                    document = self.doc
                    )

                    for name in uts.xpath('talker//name'):
                        if name.get('role') == 'metadata':
                            namemd = name.text.split(', ')
                            if len(namemd) == 1:
                                names = namemd[0]
                            else:
                                names = namemd[1] + ' ' + namemd[0]

                    # match speaker to database:
                    info_dict = {}
                    for nameidxp in uts.xpath('talker/name.id/text()'): info_dict['nameid'] = nameidxp
                    for partyxp in uts.xpath('talker/party/text()'): info_dict['party'] = partyxp
                    for electoratexp in uts.xpath('talker/electorate/text()'): info_dict['electorate'] = electoratexp
                    for rolexp in uts.xpath('talker/role/text()'): info_dict['role'] = rolexp
                    info_dict['pp'] = self.pp
                    info_dict['session'] = self.session
                    info_dict['date'] = self.date

                    speaker = find_person_in_db_aph(names, add_info=info_dict, verbosity=self.v)

                    if speaker is None:
                        print(namemd[1],namemd[0])

                    ut = pm.Utterance(
                        document=self.doc,
                        speaker=speaker,
                        agenda_item = agenda_item,
                        #speaker_role=speaker_role
                    )
                    ut.save()

                    for j in uts.xpath('following-sibling::talk.text'):
                        for k in j.iter('span'):
                            if k.get('class') == "HPS-Normal" or k.get('class') == "HPS-Small" or k.get('class') == None:
                                if k.text is not None:
                                    text1 = re.sub('\)\:', '', k.text.strip()).strip()
                                    para = self.create_paragraph(text1, ut)
                            if k.get('class') == "HPS-Normal" or k.get('class') == "HPS-Small" or k.get('class') == None or k.get('class') == "HPS-Time":
                                if k.tail:
                                    text2 = re.sub('\)\:', '', k.tail.strip()).strip()
                                    para = self.create_paragraph(text2, ut)

                            for a in k.iter('a'):
                                if a.get("type") == "MemberInterjecting":
                                    # identify speaker
                                    for name in a.iter('span'): namemd_inj = name.text.strip()
                                    names_inj = namemd_inj[0].strip(':')

                                    # match speaker to database:
                                    info_dict = {}
                                    info_dict['nameid'] = a.get("href")
                                    info_dict['pp'] = self.pp
                                    info_dict['session'] = self.session
                                    info_dict['date'] = self.date

                                    speaker_inj = find_person_in_db_aph(names_inj, add_info=info_dict, verbosity=self.v)

                                    if speaker_inj is None:
                                        print(namemd_inj[1], namemd_inj[0])

                                    # add text
                                    inj = self.add_interjection(a.tail.strip(), speaker_inj, para)

                                elif a.get("type") == "MemberContinuation":
                                    # create new utterance due to inconsistency in "continuing" members
                                    # identify speaker
                                    for name in a.iter('span'): namemd_con = name.text.strip()
                                    names_con = namemd_con[0].strip(':')

                                    # match speaker to database:
                                    info_dict = {}
                                    info_dict['nameid'] = a.get("href")
                                    info_dict['pp'] = self.pp
                                    info_dict['session'] = self.session
                                    info_dict['date'] = self.date

                                    speaker_con = find_person_in_db_aph(names_con, add_info=info_dict, verbosity=self.v)

                                    if speaker_con is None:
                                        print(namemd_con[1], namemd_con[0])

                                    ut = pm.Utterance(
                                    document=self.doc,
                                    speaker=speaker_con,
                                    agenda_item = agenda_item,
                                    )
                                    ut.save()

                                    para = self.create_paragraph(a.tail.strip(), ut)
# =================================================================================================================
# main execution script
if __name__ == '__main__':

    sys.stdout = Logger()

    single_doc = True
    replace_docs = False

    delete_all_words = False
    delete_all_parties = False
    delete_all_people = False
    delete_additional_persons = False

    if delete_all_words:
        print("Deleting all documents, utterances, paragraphs and interjections.")
        pm.Interjection.objects.all().delete()
        pm.Paragraph.objects.all().delete()
        pm.Utterance.objects.all().delete()
        pm.Document.objects.all().delete()
        print("Deletion done.")

    if delete_all_parties:
        print("Deleting all parties added.")
        pm.Party.objects.all().delete()

    if delete_all_people:
        print("Deleting all people added.")
        pm.Person.objects.all().delete()

    if delete_additional_persons:
        print("Deleting all persons added from protocol parsing.")
        pm.Person.objects.filter(information_source__startswith="from protocol scraping").delete()

    if single_doc:
        # single file
        xml_file = os.path.join(xml_path, "163-5858.xml")

        print("reading from {}".format(xml_file))

        xtree = etree.parse(xml_file)
        etree.strip_tags(xtree, 'inline')
        parser = parse_xml_items(xtree)

        parser.run()
        print("Done.")

        exit()

    # go through all scripts iteratively
    for pperiod in range(13, 12, -1):
            for session in range(0, 300):

                xml_file = os.path.join(tei_path, "{wp:02d}/BT_{wp:02d}_{sn:03d}.xml".format(wp=pperiod, sn=session))

                if os.path.isfile(xml_file):
                    print("reading from {}".format(xml_file))

                    xtree = etree.parse(xml_file)
                    etree.strip_tags(xtree, 'inline')
                    if replace_docs:
                        pm.Document.objects.filter(parlperiod__n=pp, sitting=session).delete()
                    pm.Document.objects.filter(parlperiod__n=pp, sitting=session,
                                               text_source__startswith="GermaParlTEI from ").delete()

                    parser = parse_tei_items(xtree, period=pperiod, session=session)
                    parser.run()

                    print("Done")
                    exit()
