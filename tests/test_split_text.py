import pytest

from scitrans.create_training_data.match_languages import split_text

# Each tuple is (description, en_text, fr_text). The only assertion is that split_text
# produces the same number of sentences on both sides. Failures pinpoint cases where
# the splitter handles EN punctuation differently from FR punctuation.

PLAIN_PAIRS = [
    ("plain period",
     "The cat sat on the mat.",
     "Le chat s'est assis sur le tapis."),
    
    ("plain question",
     "Where is the report?",
     "Ou est le rapport?"),
    
    ("plain exclamation",
     "What a result!",
     "Quel resultat!"),
    
    ("no terminal punctuation",
     "Hello world",
     "Bonjour le monde"),
    
    ("trailing whitespace only",
     "   ",
     "   "),
    
    ("empty string",
     "",
     ""),
    
    ("single word with period",
     "Yes.",
     "Oui."),
    
    ("two words",
     "Hello world.",
     "Bonjour le monde."),
    
    ("single character",
     "A.",
     "A."),
    
    ("ellipsis only",
     "...",
     "..."),
]

NUMBER_PAIRS = [
    ("decimal number mid-sentence",
     "The fish was 1.5 meters long.",
     "Le poisson mesurait 1,5 metres de long."),
    
    ("decimal number at end of sentence",
     "The recorded value was 1.5.",
     "La valeur enregistree etait 1,5."),
    
    ("integer at end of sentence",
     "The count was 42.",
     "Le compte etait de 42."),
    
    ("percentage mid-sentence",
     "Coverage reached 95.5 percent across the area.",
     "La couverture a atteint 95,5 pour cent sur la zone."),
    
    ("percentage symbol",
     "Coverage reached 95.5%.",
     "La couverture a atteint 95,5 %."),
    
    ("number with hyphen range",
     "Samples 1-5 were processed.",
     "Les echantillons 1-5 ont ete traites."),
    
    ("ratio with colon",
     "The ratio was 3:1 in favour of females.",
     "Le ratio etait de 3:1 en faveur des femelles."),
    
    ("ratio with spaces",
     "The ratio was 3 : 1 in favour of females.",
     "Le ratio etait de 3 : 1 en faveur des femelles."),
    
    ("temperature mid-sentence",
     "Water was 10 degrees C at depth.",
     "L'eau etait a 10 degres C en profondeur."),
    
    ("temperature with degree symbol",
     "Water was 10 degC at depth.",
     "L'eau etait a 10 degC en profondeur."),
    
    ("currency",
     "The cost was $1.5 million for the survey.",
     "Le cout etait de 1,5 million de dollars pour le releve."),
    
    ("multiple decimals one sentence",
     "Catches were 1.2, 3.4, and 5.6 tonnes.",
     "Les captures etaient de 1,2, 3,4 et 5,6 tonnes."),
    
    ("year only sentence",
     "The data covers 2010.",
     "Les donnees couvrent 2010."),
    
    ("year range",
     "The data covers 2010-2020.",
     "Les donnees couvrent 2010-2020."),
    
    ("version number",
     "We used software version 2.5.1 for the analysis.",
     "Nous avons utilise la version 2.5.1 du logiciel pour l'analyse."),
    
    ("ISBN-style number",
     "Refer to ISBN 978-3-16-148410-0 for the source.",
     "Voir ISBN 978-3-16-148410-0 pour la source."),
    
    ("decimal at start",
     "1.5 is the value we recorded.",
     "1,5 est la valeur que nous avons enregistree."),
    
    ("zero with decimal",
     "The bias was 0.0 across all trials.",
     "Le biais etait de 0,0 dans tous les essais."),
    
    ("scientific notation",
     "Density was 1.2 x 10^6 cells per litre.",
     "La densite etait de 1,2 x 10^6 cellules par litre."),
]

REFERENCE_PAIRS = [
    ("Fig. reference mid-sentence",
     "See Fig. 1 for the trend.",
     "Voir Fig. 1 pour la tendance."),
    
    ("Figure reference (long form)",
     "See Figure 1 for the trend.",
     "Voir Figure 1 pour la tendance."),
    
    ("Figs. plural reference",
     "See Figs. 1 and 2 for trends.",
     "Voir Figs. 1 et 2 pour les tendances."),
    
    ("Table reference mid-sentence",
     "Refer to Table 2 for results.",
     "Voir Tableau 2 pour les resultats."),
    
    ("Sec. reference",
     "Details are in Sec. 4.1 of the appendix.",
     "Les details sont dans la sec. 4.1 de l'annexe."),
    
    ("Vol. and No. reference",
     "Published in Vol. 3 No. 2 last year.",
     "Publie dans le vol. 3 no. 2 l'an dernier."),
    
    ("pp. page range",
     "Reference pp. 12-15 for context.",
     "Reference pp. 12-15 pour le contexte."),
    
    ("p. single page",
     "The result is on p. 12 of the report.",
     "Le resultat est a la p. 12 du rapport."),
    
    ("ch. chapter reference",
     "See ch. 3 for background.",
     "Voir ch. 3 pour le contexte."),
    
    ("App. appendix reference",
     "See the data in App. A.",
     "Voir les donnees dans l'ann. A."),
    
    ("eq. equation reference",
     "Apply Eq. 2 to compute biomass.",
     "Appliquer l'eq. 2 pour calculer la biomasse."),
    
    ("multiple Fig. references",
     "Compare Fig. 1, Fig. 2, and Fig. 3 carefully.",
     "Comparer Fig. 1, Fig. 2 et Fig. 3 attentivement."),
]

HONORIFIC_PAIRS = [
    ("Dr. before name",
     "Dr. Smith led the analysis.",
     "Le Dr. Smith a dirige l'analyse."),
    
    ("Mr. before name",
     "Mr. Jones reviewed the data.",
     "M. Jones a revu les donnees."),
    
    ("Mrs. before name",
     "Mrs. Brown chaired the meeting.",
     "Mme Brown a preside la reunion."),
    
    ("Ms. before name",
     "Ms. Lee submitted the report.",
     "Mme Lee a soumis le rapport."),
    
    ("Prof. before name",
     "Prof. Tremblay co-authored the paper.",
     "Le Prof. Tremblay a coecrit l'article."),
    
    ("Hon. before name",
     "Hon. Member Brown attended.",
     "L'hon. Brown etait present."),
    
    ("Rev. before name",
     "Rev. Father Smith led the prayer.",
     "Le rev. pere Smith a dirige la priere."),
    
    ("Mt. before mountain name",
     "Mt. Logan dominates the range.",
     "Le mont Logan domine la chaine."),
    
    ("St. before saint name",
     "St. John's is the capital.",
     "St. Jean est la capitale."),
    
    ("Ste. before saint name",
     "Ste. Anne is a popular shrine.",
     "Ste. Anne est un sanctuaire populaire."),
    
    ("Mr. and Mrs. together",
     "Mr. and Mrs. Smith arrived.",
     "M. et Mme Smith sont arrives."),
    
    ("single initial in name",
     "J. Smith led the survey.",
     "J. Tremblay a dirige le releve."),
    
    ("multiple initials in name",
     "J. R. R. Tolkien wrote books.",
     "J. R. R. Tolkien a ecrit des livres."),
    
    ("hyphenated initial French",
     "J.-P. Tremblay co-led the study.",
     "J.-P. Tremblay a codirige l'etude."),
]

CITATION_PAIRS = [
    ("et al. citation",
     "Smith et al. reported similar findings.",
     "Smith et al. ont rapporte des resultats similaires."),
    
    ("et coll. French citation form",
     "Smith and coll. reported similar findings.",
     "Smith et coll. ont rapporte des resultats similaires."),
    
    ("parenthetical citation",
     "The trend was clear (Smith 2020).",
     "La tendance etait claire (Smith 2020)."),
    
    ("parenthetical et al. citation",
     "The trend was clear (Smith et al. 2020).",
     "La tendance etait claire (Smith et al. 2020)."),
    
    ("multiple citations",
     "The trend was clear (Smith 2020; Jones 2018; Brown 2015).",
     "La tendance etait claire (Smith 2020; Jones 2018; Brown 2015)."),
    
    ("citation with comma",
     "The trend was clear (Smith, 2020).",
     "La tendance etait claire (Smith, 2020)."),
    
    ("DOI reference",
     "See doi.org/10.1234/abc for the source.",
     "Voir doi.org/10.1234/abc pour la source."),
    
    ("bracketed reference number",
     "The result is well-known [1] in the field.",
     "Le resultat est bien connu [1] dans le domaine."),
]

DATE_PAIRS = [
    ("Jan. month",
     "The survey began on Jan. 15.",
     "Le releve a commence le 15 janv."),
    
    ("Feb. month with French accent",
     "The next survey was on Feb. 3.",
     "Le prochain releve etait le 3 fevr."),
    
    ("Mar. month",
     "Sampling began on Mar. 1.",
     "L'echantillonnage a commence le 1 mars."),
    
    ("Apr. month",
     "Reports were filed in Apr. 2024.",
     "Les rapports ont ete deposes en avr. 2024."),
    
    ("Aug. month",
     "Aug. data shows the peak.",
     "Les donnees d'aout montrent le pic."),
    
    ("Sept. month",
     "Sampling continued through Sept. 30.",
     "L'echantillonnage s'est poursuivi jusqu'au 30 sept."),
    
    ("Oct. month",
     "The cruise ended in Oct. 2023.",
     "La campagne s'est terminee en oct. 2023."),
    
    ("Nov. month",
     "Data was reviewed in Nov. last year.",
     "Les donnees ont ete examinees en nov. l'an dernier."),
    
    ("Dec. month",
     "The data was finalised in Dec. 2024.",
     "Les donnees ont ete finalisees en dec. 2024."),
    
    ("full date with year",
     "The survey began on Jan. 15, 2024.",
     "Le releve a commence le 15 janv. 2024."),
    
    ("date range across months",
     "Sampling ran from Mar. 15 to Apr. 30 last year.",
     "L'echantillonnage s'est deroule du 15 mars au 30 avr. l'an dernier."),
    
    ("time of day morning",
     "The vessel left at 6:30 a.m. on Monday.",
     "Le navire est parti a 6 h 30 lundi."),
    
    ("time of day evening",
     "The meeting ended at 8:45 p.m. that day.",
     "La reunion s'est terminee a 20 h 45 ce jour-la."),
]

LATIN_AND_INLINE_PAIRS = [
    ("e.g. inline",
     "Use a primary color, e.g., red, for the marker.",
     "Utilisez une couleur primaire, p. ex., rouge, pour le marqueur."),
    
    ("i.e. inline",
     "The result, i.e., the mean value, was reported.",
     "Le resultat, c.-a-d. la valeur moyenne, a ete rapporte."),
    
    ("etc. mid-sentence",
     "We tested red, blue, green, etc., across all sites.",
     "Nous avons teste le rouge, le bleu, le vert, etc., sur tous les sites."),
    
    ("etc. at end",
     "We tested red, blue, green, etc.",
     "Nous avons teste le rouge, le bleu, le vert, etc."),
    
    ("cf. inline",
     "Compare cf. Smith 2020 for context.",
     "Comparer cf. Smith 2020 pour le contexte."),
    
    ("ca. circa",
     "The colony dates from ca. 1950.",
     "La colonie date d'env. 1950."),
    
    ("approx. mid-sentence",
     "The catch was approx. 50 tonnes total.",
     "La capture etait d'env. 50 tonnes au total."),
    
    ("vs. mid-sentence",
     "Catch was high vs. last year.",
     "La capture etait elevee p. r. a. l'an dernier."),
    
    ("min. and max. mid-sentence",
     "Values ranged from min. 2 to max. 8 m.",
     "Les valeurs allaient de min. 2 a max. 8 m."),
    
    ("op. cit. classic",
     "See op. cit. for full discussion.",
     "Voir op. cit. pour la discussion complete."),
    
    ("ibid. inline",
     "Reported in ibid. p. 24 of the source.",
     "Rapporte dans ibid. p. 24 de la source."),
    
    ("viz. inline",
     "Three species, viz. cod, herring, and mackerel, were observed.",
     "Trois especes, soit la morue, le hareng et le maquereau, ont ete observees."),
]

SCIENTIFIC_ABBREVIATION_PAIRS = [
    ("spp. species plural",
     "Multiple Gadus spp. were collected.",
     "Plusieurs Gadus spp. ont ete recueillis."),
    
    ("sp. species singular",
     "One Sebastes sp. was identified.",
     "Un Sebastes sp. a ete identifie."),
    
    ("subsp. subspecies",
     "The subsp. mentella variant was observed.",
     "La variante subsp. mentella a ete observee."),
    
    ("var. variety",
     "The var. typica is widespread here.",
     "La var. typica est repandue ici."),
    
    ("Inc. company",
     "Acme Inc. provided the equipment.",
     "Acme inc. a fourni l'equipement."),
    
    ("Ltd. company",
     "Marine Services Ltd. ran the survey.",
     "Marine Services ltee a effectue le releve."),
    
    ("Co. company",
     "Northern Co. owns the vessel.",
     "Northern Co. est proprietaire du navire."),
    
    ("Dept. department",
     "The Dept. of Fisheries published the report.",
     "Le Dept. des Peches a publie le rapport."),
    
    ("Univ. university",
     "Submitted to Dalhousie Univ. for review.",
     "Soumis a l'univ. Dalhousie pour examen."),
]

GEOGRAPHIC_PAIRS = [
    ("U.S.A. with periods",
     "The team travelled to the U.S.A. for fieldwork.",
     "L'equipe s'est rendue aux E.-U. pour le travail de terrain."),
    
    ("U.K. with periods",
     "The lab is in the U.K.",
     "Le laboratoire est au R.-U."),
    
    ("B.C. province",
     "The data is from B.C. coastal waters.",
     "Les donnees proviennent des eaux cotieres de la C.-B."),
    
    ("N.S. province",
     "Sampling occurred in N.S. waters.",
     "L'echantillonnage a eu lieu dans les eaux de la N.-E."),
    
    ("P.E.I. province",
     "Surveys ran along P.E.I. shores.",
     "Les releves se sont deroules le long des cotes de l'I.-P.-E."),
    
    ("N.L. province",
     "The vessel docked in N.L. ports.",
     "Le navire a accoste dans les ports de T.-N.-L."),
    
    ("DFO acronym at end",
     "Data was provided by DFO.",
     "Les donnees ont ete fournies par le MPO."),
    
    ("CSAS acronym",
     "The CSAS process governs peer review.",
     "Le processus du SCCS regit l'examen par les pairs."),
    
    ("city name with St.",
     "St. John's hosted the meeting.",
     "St. Jean a accueilli la reunion."),
    
    ("city name with Mt.",
     "Mt. Pearl is just south of the city.",
     "Mt. Pearl se trouve juste au sud de la ville."),
]

QUOTE_PAIRS = [
    ("quoted speech with period inside (straight quotes)",
     'He said, "Hello there."',
     'Il a dit, "Bonjour."'),
    
    ("quoted speech with French guillemets",
     'He said, "Hello there."',
     "Il a dit, Bonjour la."),
    
    ("question with quoted phrase",
     'She asked, "Why?"',
     "Elle a demande, Pourquoi?"),
    
    ("exclamation with quoted phrase",
     'She shouted, "Stop!"',
     "Elle a crie, Arrete!"),
    
    ("quote then continuation",
     'He said, "Done." She nodded.',
     'Il a dit, "Fait." Elle a hoche la tete.'),
    
    ("colon then quoted statement",
     'The report concludes: "The stock is stable."',
     'Le rapport conclut : "Le stock est stable."'),
    
    ("nested quotes",
     'He said, "She said \'hi\' to me."',
     'Il a dit, "Elle m\'a dit \'salut\'."'),
]

PUNCTUATION_PAIRS = [
    ("em-dash parenthetical",
     "The result - surprising - was clear.",
     "Le resultat - surprenant - etait clair."),
    
    ("colon then continuation",
     "The conclusion is clear: the stock is stable.",
     "La conclusion est claire : le stock est stable."),
    
    ("semicolon mid-sentence",
     "The data is sparse; further sampling is needed.",
     "Les donnees sont rares; un echantillonnage supplementaire est necessaire."),
    
    ("ellipsis mid-sentence",
     "The trend continued... but slowly.",
     "La tendance s'est poursuivie... mais lentement."),
    
    ("ellipsis at end",
     "The story continued...",
     "L'histoire a continue..."),
    
    ("exclamation question combined",
     "Really?! That is surprising.",
     "Vraiment?! C'est surprenant."),
    
    ("multiple exclamations",
     "Wow!! What a result!!",
     "Wow!! Quel resultat!!"),
    
    ("interrobang style",
     "Why?!",
     "Pourquoi?!"),
    
    ("URL preserves periods",
     "Visit www.example.com for details.",
     "Visitez www.example.com pour les details."),
    
    ("email address",
     "Email john.smith@example.com for access.",
     "Ecrivez a john.smith@example.com pour l'acces."),
    
    ("file path",
     "The file is at /var/log/app.log on disk.",
     "Le fichier se trouve a /var/log/app.log sur le disque."),
    
    ("hyphenated compound",
     "The well-known result was confirmed.",
     "Le resultat bien connu a ete confirme."),
    
    ("dash separator",
     "Result -- confirmed -- by all reviewers.",
     "Resultat -- confirme -- par tous les examinateurs."),
]

TWO_SENTENCE_PAIRS = [
    ("two simple sentences",
     "The cat sat on the mat. The dog stood beside it.",
     "Le chat s'est assis sur le tapis. Le chien se tenait a cote."),
    
    ("statement then question",
     "The data is ready. Have you reviewed it?",
     "Les donnees sont pretes. Les avez-vous examinees?"),
    
    ("question then statement",
     "Are you ready? Let us begin the meeting.",
     "Es-tu pret? Commencons la reunion."),
    
    ("two questions in a row",
     "Are you ready? Have you read the report?",
     "Es-tu pret? As-tu lu le rapport?"),
    
    ("two exclamations",
     "Stop right there! Do not move!",
     "Arrete tout de suite! Ne bouge pas!"),
    
    ("Fig. reference then continuation",
     "See Fig. 1 for trends. The data spans ten years.",
     "Voir Fig. 1 pour les tendances. Les donnees couvrent dix ans."),
    
    ("et al. citation then continuation",
     "Smith et al. published in 2020. The work was novel.",
     "Smith et al. ont publie en 2020. Le travail etait novateur."),
    
    ("decimal then new sentence",
     "The value was 1.5. We then measured again.",
     "La valeur etait 1,5. Nous avons alors mesure de nouveau."),
    
    pytest.param(
        "date then continuation",
        "The survey began on Jan. 15. It ran for two weeks.",
        "Le releve a commence le 15 janv. Il a dure deux semaines.",
        marks=pytest.mark.xfail(reason="structural-ambiguity - period serves multiple roles")
    ),
    
    ("date with year then continuation",
     "The survey began on Jan. 15, 2024. It ran for two weeks.",
     "Le releve a commence le 15 janv. 2024. Il a dure deux semaines."),
    
    ("month at end then continuation",
     "Sampling ended in Sept. The data was reviewed.",
     "L'echantillonnage s'est termine en sept. Les donnees ont ete examinees."),
    
    ("multiple punctuation then continuation",
     "What?! Are you serious?",
     "Quoi?! Es-tu serieux?"),
    
    ("quote then continuation",
     'He said, "Done." She nodded.',
     'Il a dit, "Fait." Elle a hoche la tete.'),
    
    ("section ref then continuation",
     "Refer to Sec. 4.1 first. Then proceed to the analysis.",
     "Referez-vous a la sec. 4.1 d'abord. Puis passez a l'analyse."),
    
    ("page range then continuation",
     "See pp. 12-15 for the methodology. The results follow.",
     "Voir pp. 12-15 pour la methodologie. Les resultats suivent."),
    
    ("Mr./Mrs. then continuation",
     "Mr. and Mrs. Smith attended the meeting. They spoke briefly.",
     "M. et Mme Smith ont assiste a la reunion. Ils ont parle brievement."),
    
    ("etc. then continuation",
     "We sampled cod, herring, mackerel, etc. The list goes on.",
     "Nous avons echantillonne morue, hareng, maquereau, etc. La liste continue."),
    
    ("acronym at end then continuation",
     "Data was provided by DFO. The report followed.",
     "Les donnees ont ete fournies par le MPO. Le rapport a suivi."),
    
    ("question with citation then continuation",
     "Are these trends real (Smith 2020)? Further work is needed.",
     "Ces tendances sont-elles reelles (Smith 2020)? Des travaux supplementaires sont necessaires."),
    
    ("ellipsis then sentence",
     "The trend continued... but recovery was slow. We expect more years of decline.",
     "La tendance s'est poursuivie... mais le retablissement a ete lent. Nous prevoyons d'autres annees de declin."),
    
    ("two short sentences",
     "Yes. No.",
     "Oui. Non."),
    
    pytest.param(
        "three short sentences",
        "Yes. No. Maybe.",
        "Oui. Non. Peut-etre.",
        marks=pytest.mark.xfail(reason="structural-ambiguity - period serves multiple roles")
    ),
]

PARAGRAPH_PAIRS = [
    ("four short sentences",
     "First. Second. Third. Fourth.",
     "Premier. Deuxieme. Troisieme. Quatrieme."),
    
    ("five short sentences",
     "One. Two. Three. Four. Five.",
     "Un. Deux. Trois. Quatre. Cinq."),
    
    ("scientific summary with citations",
     "The stock has declined since 2010. Smith et al. reported similar trends in adjacent areas. "
     "Recovery is expected to take a decade. Management measures are under review.",
     "Le stock a diminue depuis 2010. Smith et al. ont rapporte des tendances similaires dans les zones adjacentes. "
     "Le retablissement devrait prendre une decennie. Les mesures de gestion sont en cours d'examen."),
    
    ("methods paragraph with abbreviations",
     "Samples were collected weekly. Each sample was 1.5 L in volume. "
     "Analysis followed the method in Sec. 4.2. See Fig. 3 for the timeline.",
     "Les echantillons ont ete preleves chaque semaine. Chaque echantillon avait un volume de 1,5 L. "
     "L'analyse a suivi la methode de la sec. 4.2. Voir Fig. 3 pour le calendrier."),
    
    ("results paragraph with numbers",
     "The mean was 12.4 kg. The maximum reached 18.7 kg. The minimum was 6.2 kg. "
     "Variance was high across sites.",
     "La moyenne etait de 12,4 kg. Le maximum a atteint 18,7 kg. Le minimum etait de 6,2 kg. "
     "La variance etait elevee entre les sites."),
    
    ("discussion with parenthetical citations",
     "Recruitment is variable (Jones 2018). Stock biomass has rebounded recently (Smith et al. 2020). "
     "Future projections remain uncertain.",
     "Le recrutement est variable (Jones 2018). La biomasse du stock a recemment rebondi (Smith et al. 2020). "
     "Les projections futures demeurent incertaines."),
    
    ("recommendations list-like",
     "We recommend three actions. First, expand the survey area. Second, increase sampling frequency. "
     "Third, share data with partners.",
     "Nous recommandons trois actions. Premierement, etendre la zone de releve. Deuxiemement, augmenter la frequence d'echantillonnage. "
     "Troisiemement, partager les donnees avec les partenaires."),
    
    ("dates and months mixed",
     "Sampling ran from Jan. 15 to Mar. 30. Results were reported in Apr. The next survey is planned for Sept.",
     "L'echantillonnage s'est deroule du 15 janv. au 30 mars. Les resultats ont ete rapportes en avr. Le prochain releve est prevu pour sept."),
    
    ("question and answer",
     "What drives the decline? Several factors are likely. Climate change, fishing pressure, and habitat loss all play a role.",
     "Qu'est-ce qui motive le declin? Plusieurs facteurs sont probables. Le changement climatique, la pression de peche et la perte d'habitat jouent tous un role."),
    
    ("figures and tables together",
     "See Fig. 1 and Fig. 2 for spatial trends. Table 1 summarises the catch data. "
     "Refer to Sec. 5 for further discussion.",
     "Voir Fig. 1 et Fig. 2 pour les tendances spatiales. Le Tableau 1 resume les donnees de capture. "
     "Voir la sec. 5 pour une discussion plus approfondie."),
    
    ("acronyms then continuation",
     "DFO leads the assessment. The CSAS process governs peer review. Reports are published online.",
     "Le MPO dirige l'evaluation. Le processus du SCCS regit l'examen par les pairs. Les rapports sont publies en ligne."),
    
    ("decimals throughout",
     "Mean catch was 4.2 t. Median was 3.8 t. Maximum was 9.5 t. Minimum was 1.1 t.",
     "La capture moyenne etait de 4,2 t. La mediane etait de 3,8 t. Le maximum etait de 9,5 t. Le minimum etait de 1,1 t."),
    
    ("mixed quotes and citations",
     'The author wrote, "Recovery is uncertain." Smith et al. agreed. The committee concurred.',
     'L\'auteur a ecrit, "Le retablissement est incertain." Smith et al. ont approuve. Le comite a convenu.'),
    
    ("paragraph with newlines",
     "First sentence.\nSecond sentence.\nThird sentence.",
     "Premiere phrase.\nDeuxieme phrase.\nTroisieme phrase."),
    
    ("multiple spaces between sentences",
     "First sentence.   Second sentence.   Third sentence.",
     "Premiere phrase.   Deuxieme phrase.   Troisieme phrase."),
    
    ("trailing space at end",
     "First. Second. Third.   ",
     "Premier. Deuxieme. Troisieme.   "),
    
    ("leading space at start",
     "   First. Second. Third.",
     "   Premier. Deuxieme. Troisieme."),
    
    ("species-heavy paragraph",
     "Gadus morhua was dominant. Several Sebastes spp. were also observed. One Hippoglossus sp. was caught.",
     "Gadus morhua dominait. Plusieurs Sebastes spp. ont egalement ete observes. Un Hippoglossus sp. a ete capture."),
    
    ("organisation-heavy paragraph",
     "DFO funded the work. Acme Inc. supplied equipment. The Univ. of Halifax processed the samples.",
     "Le MPO a finance les travaux. Acme inc. a fourni l'equipement. L'univ. d'Halifax a traite les echantillons."),
    
    ("citation cluster paragraph",
     "Multiple studies confirm the trend (Smith 2020; Jones et al. 2018; Brown 2015). The decline is well-documented. Recovery remains uncertain.",
     "Plusieurs etudes confirment la tendance (Smith 2020; Jones et al. 2018; Brown 2015). Le declin est bien documente. Le retablissement demeure incertain."),
    
    ("figure references throughout",
     "See Fig. 1. See Fig. 2. See Fig. 3. See Fig. 4.",
     "Voir Fig. 1. Voir Fig. 2. Voir Fig. 3. Voir Fig. 4."),
    
    ("realistic abstract paragraph",
     "This assessment summarises the status of cod (Gadus morhua) in 4VsW. "
     "Catches averaged 1.5 kt over the period 2010-2024. "
     "Recruitment has been below average since 2015 (Smith et al. 2022). "
     "Spawning stock biomass is currently estimated at 12,500 t. "
     "Recovery to the LRP is unlikely before 2030.",
     "Cette evaluation resume l'etat de la morue (Gadus morhua) dans 4VsW. "
     "Les captures se sont etablies en moyenne a 1,5 kt sur la periode 2010-2024. "
     "Le recrutement est inferieur a la moyenne depuis 2015 (Smith et al. 2022). "
     "La biomasse du stock reproducteur est actuellement estimee a 12 500 t. "
     "Le retablissement au PRL est peu probable avant 2030."),
]

EDGE_CASE_PAIRS = [
    ("only period",
     ".",
     "."),
    
    ("only question mark",
     "?",
     "?"),
    
    ("only exclamation",
     "!",
     "!"),
    
    ("comma only",
     ",",
     ","),
    
    ("two periods only",
     "..",
     ".."),
    
    ("number only",
     "42",
     "42"),
    
    ("number with period",
     "42.",
     "42."),
    
    ("date only",
     "Jan. 15.",
     "Le 15 janv."),
    
    ("just a citation",
     "(Smith 2020)",
     "(Smith 2020)"),
    
    ("multiple newlines",
     "First.\n\n\nSecond.",
     "Premier.\n\n\nDeuxieme."),
    
    ("mixed line endings",
     "First.\r\nSecond.\nThird.",
     "Premier.\r\nDeuxieme.\nTroisieme."),
    
    ("tab between sentences",
     "First.\tSecond.",
     "Premier.\tDeuxieme."),
    
    ("very long single sentence",
     "The exhaustive analysis of cod catch data over the past two decades, accounting for environmental drivers, fishing effort, recruitment variability, and climate-driven shifts in distribution, "
     "indicates a complex picture that requires continued monitoring.",
     "L'analyse exhaustive des donnees de capture de la morue au cours des deux dernieres decennies, tenant compte des facteurs environnementaux, de l'effort de peche, de la variabilite du "
     "recrutement et des changements de distribution lies au climat, indique un tableau complexe qui necessite une surveillance continue."),
    
    ("sentence ending in abbreviation",
     "The analysis was completed by Mr.",
     "L'analyse a ete realisee par M."),
    
    ("sentence ending in et al.",
     "The study was led by Smith et al.",
     "L'etude a ete dirigee par Smith et al."),
    
    ("only an abbreviation",
     "Fig. 1.",
     "Fig. 1."),
    
    ("starts with abbreviation",
     "Fig. 1 shows the trend.",
     "Fig. 1 montre la tendance."),
    
    ("ends with parenthetical citation",
     "The result was clear (Smith 2020).",
     "Le resultat etait clair (Smith 2020)."),
    
    ("ends with question and citation",
     "Was the trend real (Smith 2020)?",
     "La tendance etait-elle reelle (Smith 2020)?"),
    
    ("ends with exclamation and citation",
     "What a finding (Smith 2020)!",
     "Quelle decouverte (Smith 2020)!"),
]

ALL_PAIRS = (
        PLAIN_PAIRS
        + NUMBER_PAIRS
        + REFERENCE_PAIRS
        + HONORIFIC_PAIRS
        + CITATION_PAIRS
        + DATE_PAIRS
        + LATIN_AND_INLINE_PAIRS
        + SCIENTIFIC_ABBREVIATION_PAIRS
        + GEOGRAPHIC_PAIRS
        + QUOTE_PAIRS
        + PUNCTUATION_PAIRS
        + TWO_SENTENCE_PAIRS
        + PARAGRAPH_PAIRS
        + EDGE_CASE_PAIRS
)


@pytest.mark.parametrize(
    "description, en_text, fr_text",
    ALL_PAIRS,
    ids=[p.values[0] if hasattr(p, "values") else p[0] for p in ALL_PAIRS],
)
def test_split_text_en_fr_same_count(description, en_text, fr_text):
    en_sentences = split_text(en_text)
    fr_sentences = split_text(fr_text)
    assert len(en_sentences) == len(fr_sentences), (
        f"\n[{description}]\n"
        f"  EN ({len(en_sentences)}): {en_sentences}\n"
        f"  FR ({len(fr_sentences)}): {fr_sentences}"
    )
