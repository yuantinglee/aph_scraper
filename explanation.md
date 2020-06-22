### Building models:

- refer to README on the github repo here [https://github.com/yuantinglee/aph_scraper](https://github.com/yuantinglee/aph_scraper)
- This should be done for the current APSIS server

### Parsing XML text info:

There are three different xml versions in the data provided by Australian Parliament Hansard:

- 2.0
- 2.1
- 2.2

The versions can be identified in the following manner:

```
import lxml.etree as etree
tree = etree.parse('xml_files/House_of_Representatives_2011_05_10_10_Official.xml')
etree.strip_tags(tree, 'inline')
root = tree.getroot()
# finding scheme type
for h in root.xpath("//hansard"):
    print(h.get("version"))
```

There are two different versions of the APH scraper - 1 and 2.

Version 1 is meant for xml versions 2.0 and 2.1, and Version 2 is meant for xml version 2.2

Example (Version 1): [https://apsis.mcc-berlin.net/parliament/document/19866/](https://apsis.mcc-berlin.net/parliament/document/19866/)
- raw file: 163-5858.xml

Example (Version 2): [https://apsis.mcc-berlin.net/parliament/document/19868/](https://apsis.mcc-berlin.net/parliament/document/19868/)
- raw file: House_of_Representatives_2011_05_10_10_Official.xml

### To Do:

- Include version identification of xml file into scraper
- Update bulk scraping code (i.e. when single_file = False)
- Run scraper for all files in `australian_downloads_coal`
