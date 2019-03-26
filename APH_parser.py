import os
import difflib
import zipfile
import lxml.etree as etree
import random
import re
import sys
import datetime as dt
from datetime import datetime

import django
import platform

#if platform.node() == "mcc-apsis":
    #sys.path.append('/home/muef/tmv/BasicBrowser/')
    #tei_path = "/home/muef/GermaParlTEI-master"

#else:
    # local paths
    #sys.path.append('/media/Data/MCC/tmv/BasicBrowser/')
    #tei_path = "/media/Data/MCC/Parliament Germany/GermaParlTEI-master"

sys.path.append('/home/leey/Documents/Data/tmv/BasicBrowser/')
tei_path = "/home/leey/Documents/Data/australian_parliament_downloads/downloads_coal"

#sys.path.append('/home/galm/software/django/tmv/BasicBrowser/')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

# import from appended path
import parliament.models as pm
from parliament.tasks import do_search, run_tm
import cities.models as cmodels
from django.contrib.auth.models import User
import tmv_app.models as tm

from parsing_utils import POI, dehyphenate_with_space, clean_text, find_person_in_db_aph
from regular_expressions_global import POI_MARK

# ============================================================
# write output to file and terminal

import pprint
pretty_printer = pprint.PrettyPrinter(indent=4)

time_stamp = datetime.now().strftime("%y%m%d_%H%M%S")
output_file = "./parlsessions_tei_parser_output_" + time_stamp + ".log"
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
class parse_tei_items(object):

    def __init__(self, xtree, v=1, period=None, session=None):
        self.v = v
        self.divs = xtree.findall("//debate")
        self.pp = int(xtree.xpath("//parliament.no//text()")[0])
        self.session = int(re.findall(r'\b\d+\b', xtree.xpath("//session.no//text()")[0])[0])

        if period is not None:
            if period != self.pp:
                print("! Warning: period number not matching: {} {}".format(period, self.pp))

        if session is not None:
            if session != self.session:
                print("! Warning: session number not matching: {} {}".format(session, self.session))

        self.date = datetime.strptime(xtree.xpath("//date//text()")[0], '%Y-%m-%d')
        #try:
        #    self.original_source = xtree.xpath("//sourceDesc//url//text()")[0]
        #except IndexError:
        #    self.original_source = "NA"
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

    def run(self):

        self.get_or_create_objects()

        ### start parsing of speeches
        for div in self.divs:
            # either <debateinfo> or <subdebate.1>
            if self.v > 1:
                print("div type: {}".format(div.xpath("type/text()")))

            for uts in div.iter('talk.start'):
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

                #! to fix
                #speaker_role_set = pm.SpeakerRole.objects.filter(alt_names__contains={info_dict['role']})
                #if len(speaker_role_set) < 1:
                #    speaker_role = pm.SpeakerRole(name=info_dict['role'], alt_names={info_dict['role']})
                #    speaker_role.save()
                #else:
                #    speaker_role = speaker_role_set.first()
                #    if len(speaker_role_set) > 1:
                #        print("Warning: several speaker roles matching")

                ut = pm.Utterance(
                    document=self.doc,
                    speaker=speaker,
                    #speaker_role=speaker_role
                )
                ut.save()

                for c in uts.iter():
                    if self.v > 1:
                        print("{}: {}".format(c.tag, c.text))

                    if c.tag == "para":
                        if c.text:
                            para = self.create_paragraph(c.text.strip(u'\u2014'), ut)

                for j in uts.xpath('following-sibling::para|parent::*/following-sibling::para|following-sibling::*/child::para'):
                    if j.text:
                        para = self.create_paragraph(j.text.strip(u'\u2014'), ut)

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
        #wp = 18
        #session = 1

        #xml_file = os.path.join(tei_path, "{wp:02d}/BT_{wp:02d}_{sn:03d}.xml".format(wp=wp, sn=session))
        #namespaces = {'tei': 'http://www.tei-c.org/ns/1.0'}
        xml_file = os.path.join(tei_path, "6593-3.xml")

        print("reading from {}".format(xml_file))

        xtree = etree.parse(xml_file)
        etree.strip_tags(xtree, 'inline')
        parser = parse_tei_items(xtree)

        # pm.Document.objects.filter(parlperiod__n=parser.wp, sitting=parser.session).delete()
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
