# Australian Parliament Hansard scraper

This project uses models from [tmv/parliament](https://github.com/mcallaghan/tmv/tree/master/BasicBrowser/parliament) - any reference to objects are to the models found there.

Before running the parliamentary protocol parser, these scripts should first be ran in order:

- `aph_model_builder.py`

This adds the parliamentary periods of the Australian Parliament to the database as `ParlPeriod` objects.

- `aph_parliamentarian_parser.py`

This adds the members of parliament from the [AustralianPoliticians](https://github.com/RohanAlexander/AustralianPoliticians) project as `Person` objects.

- `aph_add_speakers.py`

This adds specific parliamentary roles such as Speakers and Deputy Speakers as `Post` objects, linking them to the relevant person involved.

As there are some entries that are not added with the script, they have to be manually added. This can be done in the `APH_models_builder_and_politican_parser.ipynb` under **add entries manually**. 
