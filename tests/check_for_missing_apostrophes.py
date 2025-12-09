import pandas as pd

legitimate_english = {'i', 'a', 'o'}
legitimate_french = {'à', 'a', 'y', 'ô', 'ù'}

contraction_patterns_english = {
    't': [
        'don', 'doesn', 'didn', 'won', 'wouldn', 'couldn', 'shouldn',
        'isn', 'aren', 'wasn', 'weren', 'hasn', 'haven', 'hadn',
        'ain', 'can',
    ],
    's': [
        'it', 'that', 'what', 'who', 'where', 'when', 'why', 'how',
        'there', 'here', 'everyone', 'everything', 'something',
        'nothing', 'he', 'she', 'this',
    ],
    'm': ['i'],
    'd': ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'there', 'that', 'who', 'what'],
    'll': ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'there', 'who', 'what'],
    've': ['i', 'you', 'we', 'they', 'would', 'could', 'should', 'might', 'must'],
    're': ['you', 'we', 'they', 'here', 'there', 'who', 'what'],
}

contraction_patterns_french = {
    'j': [
        'ai', 'avais', 'aurai', 'aurais', 'étais', 'avais', 'étais',
        'irai', 'irais', 'aime', 'adore', 'arrive', 'attends', 'entends',
        'espère', 'ignore', 'imagine', 'habite', 'ouvre'
    ],
    'l': [
        'a', 'est', 'avait', 'avait', 'avait', 'aurait', 'auront',
        'on', 'un', 'une', 'autre', 'homme', 'enfant', 'ami', 'amie',
        'air', 'eau', 'école', 'âge'
    ],
    'd': [
        'un', 'une', 'abord', 'accord', 'ailleurs', 'après', 'autant',
        'entre', 'eux', 'elle', 'elles', 'ici', 'où'
    ],
    'n': [
        'a', 'ai', 'as', 'avons', 'avez', 'ont', 'es', 'est', 'êtes',
        'importe'
    ],
    'm': ['as', 'a', 'en', 'y', 'appelle', 'étais', 'étaient', 'étais'],
    't': ['as', 'a', 'es', 'est', 'y', 'en', 'il', 'elle', 'on'],
    's': ['il', 'ils', 'est', 'était', 'en', 'y'],
    'c': ['est', 'était', 'a', 'en'],
    'qu': ['il', 'ils', 'elle', 'elles', 'on', 'un', 'une', 'est', 'en'],
}


def has_single_letter_word(text):
    if not isinstance(text, str):
        return False
    words = text.split()
    for word in words:
        cleaned = word.strip('.,!?;:"\'-()[]{}')
        if len(cleaned) == 1:
            return True
    return False


def get_single_letter_words(text):
    if not isinstance(text, str):
        return []
    words = text.split()
    single_letters = []
    for i, word in enumerate(words):
        cleaned = word.strip('.,!?;:"\'-()[]{}')
        if len(cleaned) == 1:
            single_letters.append((i, cleaned.lower(), word))
    return single_letters


def is_legitimate_single_letter(letter, lang):
    letter_lower = letter.lower()
    if lang == 'en':
        return letter_lower in legitimate_english
    else:
        return letter_lower in legitimate_french


def check_missing_apostrophe(text, letter_info, lang):
    if not isinstance(text, str):
        return False, None
    words = text.split()
    idx, letter, original = letter_info
    letter_lower = letter.lower()
    
    if lang == 'en':
        patterns = contraction_patterns_english
    else:
        patterns = contraction_patterns_french
    
    if letter_lower in patterns:
        if idx > 0:
            prev_word = words[idx - 1].strip('.,!?;:"\'-()[]{}').lower()
            if prev_word in patterns[letter_lower]:
                return True, f"{prev_word} {letter}"
        if idx < len(words) - 1:
            next_word = words[idx + 1].strip('.,!?;:"\'-()[]{}').lower()
            if next_word in patterns[letter_lower]:
                return True, f"{letter} {next_word}"
    
    for pattern_letter, preceding_words in patterns.items():
        if idx > 0:
            prev_word = words[idx - 1].strip('.,!?;:"\'-()[]{}').lower()
            if prev_word == letter_lower and pattern_letter in [w.strip('.,!?;:"\'-()[]{}').lower() for w in words[idx + 1:idx + 2]] if idx < len(words) - 1 else False:
                return True, f"{letter} {words[idx + 1] if idx < len(words) - 1 else ''}"
    
    return False, None


def analyze_row(row):
    issues = []
    
    if row['source_lang'] == 'en':
        en_text, fr_text = row['source'], row['target']
    else:
        en_text, fr_text = row['target'], row['source']
    
    en_singles = get_single_letter_words(en_text)
    for letter_info in en_singles:
        idx, letter, original = letter_info
        if not is_legitimate_single_letter(letter, 'en'):
            is_apostrophe, pattern = check_missing_apostrophe(en_text, letter_info, 'en')
            if is_apostrophe:
                issues.append(('english', 'missing_apostrophe', pattern, en_text))
            else:
                issues.append(('english', 'ocr_or_other', letter, en_text))
    
    fr_singles = get_single_letter_words(fr_text)
    for letter_info in fr_singles:
        idx, letter, original = letter_info
        if not is_legitimate_single_letter(letter, 'fr'):
            is_apostrophe, pattern = check_missing_apostrophe(fr_text, letter_info, 'fr')
            if is_apostrophe:
                issues.append(('french', 'missing_apostrophe', pattern, fr_text))
            else:
                issues.append(('french', 'ocr_or_other', letter, fr_text))
    
    return issues


if __name__ == '__main__':
    filename = "../../Data/training_data.jsonl"
    # filename = "../../Data/pipeline_training_data.jsonl"
    # filename = "../../Data/pipeline_testing_data.jsonl"
    
    df = pd.read_json(filename, lines=True)
    
    df['has_single_letter'] = df.apply(
        lambda row: has_single_letter_word(row['source']) or has_single_letter_word(row['target']),
        axis=1
    )
    
    filtered_df = df[df['has_single_letter']].copy()
    
    results = []
    for idx, row in filtered_df.iterrows():
        issues = analyze_row(row)
        for issue in issues:
            results.append({
                'original_index': idx,
                'source': row['source'],
                'target': row['target'],
                'source_lang': row['source_lang'],
                'language': issue[0],
                'issue_type': issue[1],
                'pattern': issue[2],
                'text_with_issue': issue[3]
            })
    
    results_df = pd.DataFrame(results)
    
    if not results_df.empty:
        results_df.to_csv("single_letter_analysis.csv", index=False)
        
        summary_df = results_df.drop_duplicates(subset=['pattern']).sort_values('pattern').reset_index(drop=True)
        summary_df.to_csv("summary_of_patterns.csv", index=False)
        
        print(f"Total rows with single letter words: {len(filtered_df)}")
        print(f"Total issues found: {len(results_df)}")
        print(f"Unique patterns: {len(summary_df)}")
        print(f"Missing apostrophe issues: {len(results_df[results_df['issue_type'] == 'missing_apostrophe'])}")
        print(f"Potential OCR issues: {len(results_df[results_df['issue_type'] == 'ocr_or_other'])}")
        print("\n--- Summary of Patterns ---")
        for _, row in summary_df.iterrows():
            print(f"{row['pattern']}\t{row['text_with_issue']}")
    else:
        print("No issues found")
    
    # TODO
    #   --- Summary of Patterns ---
    #   0	We do not present results from the 0 to 30 m here because we have not sufficiently well defined the very strong seasonal cycle for this layer yet.
    #   1	In the northeast, most of the bottom was covered by temperatures ranging from 1 to 4 C.
    #   2	Maritimes Region State of the Ocean 2 Average Conditions Temperature and salinity conditions within the Scotian Shelf, Bay of Fundy and Gulf of Maine vary spatially due to complex bottom topography, transport from upstream sources such as the Gulf of St.
    #   3	La température et la salinité augmentent généralement d'est en ouest et de la côte Région des Maritimes État de l'océan 3 au large, sous l'influence des eaux du large plus chaudes et plus salées, et de l'apport d'eau plus douce du golfe du Saint-Laurent.
    #   4	In the northeast, most of the bottom was covered by temperatures ranging from 1 to 4 C.
    #   5	Departures from normal annual mean air temperature (dashed line) and the 5 year means at Cartwright on the Labrador Coast.
    #   6	6) The conclusions that follow often refer to seismic sound and field operating conditions.
    #   7	State of the Ocean: Maritimes Region Physical Oceanographic Conditions 7 Ocean water density increases with depth and depends on temperature, salinity and pressure.
    #   8	8), the 13th lowest in the last 48 years.
    #   9	Maritimes Region State of the Eastern Scotian Shelf Ecosystem 9 In addition to the subsurface changes, there have been important changes in the near surface waters.
    #   a c	A) estimation de la densité par la méthode du noyau (EDMN) de la biomasse des poissons, reclassée en déciles; B) décile supérieur de l'EDMN provenant de A; C) résultats de l'analyse Getis-Ord Gi en matière de biomasse des poissons, indiquant les points chauds et les points froids; D) groupes de points chauds (90 99 de confiance) avec 10 points provenant de C, délimités par des polygones à enveloppe convexe.
    #   a l	La sensibilité du modele de population aux changements potentiels de croissance doit aussi etre mise a l' essai.
    #   aren t	Answer: If the United States and Canada aren t on the same page in terms of recovery, neither country will achieve their goals.
    #   b	(This dimension more readily applies to structural properties of habitats and ecological communities, but can apply to functional properties of species as well.) b.
    #   c	At the surface, the range is about 16 C but there is little or no seasonal change at depths greater than approximately 150 to 200 m.
    #   c a	Évaluations des stocks dans la région Centre Arctique (C A) et besoins analytiques.
    #   c en	Enfin, on recommande d'étudier la possibilité de réunir les zones fermées B et C en une zone fermée unique, car, selon certaines preuves, des prélèvements accidentels de coraux et d'éponges ont eu lieu entre les deux zones fermées.
    #   c est	C est pourquoi on mesure les conditions océanographiques physiques (essentiellement la température et la salinité de l'eau) lors des relevés sur les ressources effectués par les navires scientifique et régulièrement à des stations fixes dans le cadre du Programme de monitorage de la zone Atlantique (PMZA).
    #   c était	Le déclarant a indiqué qu une température de 7,98 C était la température létale moyenne pour le CGT2016 lorsque la température est réduite rapidement.
    #   can t	The temperature is going to go down a bit, but we can t predict accurately.
    #   couldn t	Some participants took the view that if it couldn t be used in this manner it should be dropped.
    #   d	to maintain populations within bounds of natural variability D.
    #   d S	SD5, the highest number of fish per cage which will maintain DMax 5 g C m-2 d-1, can then be calculated as oposed Max D D S F F S Pr 5 5 where FMax is the proposed maximum feed rate (in kg d-1 per cage), and SProposed is the proposed number of fish per cage.
    #   d accord	Etes-vous d' accord pour que soit adoptée l' approche de précaution en vue d'atteindre les objectifs de conservation dans les situations d' incertitude.
    #   d après	Résumer les tendances générales dans la taille des populations (tant dans le nombre d'individus adultes que dans le nombre total de la population) pour la période la plus longue possible et, en particulier, pour les trois dernières générations (d après l'âge moyen des géniteurs).
    #   d autres	Directives sur l'identification d' autres mesures de conservation effectives par zone dans les eaux côtières et marines du Canada.
    #   d ici	On signale qu il serait peut-être nécessaire d'envisager les effets sur l'habitat de la morue des méthodes de pêche, tel le chalutage de fond, mais on convient généralement que cette méthode ne susciterait pas de préoccupation au cours de la prochaine année environ (d ici à ce qu un plan de rétablissement soit mis en uvre) puisqu elle est utilisée dans cette même zone depuis des décennies.
    #   d où	Dans la rivière (d où proviennent les données de reconstitution des remontes), presque toutes les identifications de stock sont fondées sur l'ADN; toutefois, un faible nombre de prises en rivière peut entraîner, tôt dans la saison, une réduction des tailles d'échantillons au moment de la migration commune des saumons rouges de la rivière Stuart (hâtive) et de la rivière Chilliwack.
    #   d there	d) There is a complete lack of information on genetic techniques (as opposed to genetics as a component of biodiversity) which can provide cost-effective and vital information for a multitude of planning and monitoring purposes.
    #   d un	d) Un taux d'accroissement de la population de 2 permettrait une faible mortalité causée par l'homme.
    #   d une	Les pecheurs ont demande si la création d'' une zone tampon de 10 mi lies entre la zone 12 (auparavant la zone 25) contribuait a l'état du stock.
    #   d we	Based on this concern and the results of the Bridging Analysis (Appendix D) we conducted sensitivity analyses testing the effects of broadening of the prior distribution on q by changing the standard deviation of this prior while keeping the mean constant.
    #   d what	d) What are the strengths and weaknesses of the information supporting a), b), and c)?; and, e) What information is available related to critical habitat and or residence for this species.
    #   didn t	The point was also advanced that data didn t have to be incorporated into an analytical model to be of use in determining stock status.
    #   doesn t	There are quite a few empty cells the fishers fish in the peak the site- month interaction doesn t appear to be statistically strong.
    #   don t	General trends are stated instead.) Commercial catches will be reported as a regional total because management areas don t have any relationship to stock boundaries.
    #   e	Participants from the southern Gulf agreed that preset restrictions should be maintained (i .e.
    #   elle d	Pour cette UD, on a utilisé des connaissances spécialisées sur la gestion passée et actuelle des pêches qui ont un impact sur elle (d après la période de migration connue de l'UD et l'échantillonnage de l'ADN dans les pêches) pour estimer la gravité de l'activité de pêche future.
    #   en c	Le choix de langage a été dicté par sa nature orientée objets; il pourrait tout aussi bien avoir été écrit en C.
    #   en j	La ligne verticale tiretée représente l'année de l'expérience avec les hameçons et le passage des hameçons en J aux hameçons circulaires.
    #   en m	Sous l'état actuel de la productivité élevée du recrutement, la probabilité de rétablissement a été estimée à 27 30 ans après une réduction de 20 en M, 95 30 ans après une réduction de 30 en M, et 51 et 100 6 et 20 ans après une réduction de 40 en M.
    #   en t	Desgagnés poursuit en présentant les analyses de sensibilité qui ont été effectuées pour évaluer l'impact du choix des valeurs de certains paramètres sur les résultats simulés, dont la moyenne des captures annuelles, en zone critique, en zone saine, la variation annuelle des prises (en et en t), la biomasse moyenne et la PUE moyenne.
    #   entre d	Le déclarant indique que des hybrides interspécifiques ont été signalés entre D.
    #   est c	Ce traitement cible deux espèces de poux : Lepeophtheirus salmonis (cible principale) et Caligus elongatus (en Colombie-Britannique, la deuxième espèce d'intérêt est C.
    #   est m	Le groupe décide que la LO pour l'agriculture sera fixée à K et que le LI correspondant est M.
    #   est t	2.2 FORMULATION DU PROBLÈME 2.2.1 Détermination du danger Dans la présente évaluation des risques, le danger est T.
    #   f	f) The effects of anthropogenic sounds on the vocalisation patterns of marine mammals are well documented, but the effects of specifically seismic sounds are poor known, and warrant further study.
    #   f S	SD5, the highest number of fish per cage which will maintain DMax 5 g C m-2 d-1, can then be calculated as oposed Max D D S F F S Pr 5 5 where FMax is the proposed maximum feed rate (in kg d-1 per cage), and SProposed is the proposed number of fish per cage.
    #   g	48 Risk Assessment for the West Greenland Fishery on North American Atlantic Salmon by G.
    #   h	With a Northeast wind makes landfall in 72 hours; with a Southeast wind, land is not impacted within 46 h but if the slick moved towards East Point, it would reach land in about 2 days.
    #   hadn t	At the time of the meeting, the BGCM simulation hadn t been completed yet.
    #   hasn t	angulata occur, but have not yet been surveyed, or locate sites with optimal habitat for this species where it hasn t yet dispersed.
    #   haven t	Casselman: Haven t there been seasonal changes.
    #   he s	11, 25, 64 Su rf- pe rc he s Cymatogaster aggregata Shiner Surfperch 50-1000 200 0-150 146 Make seasonal onshore-offshore migrations over 200 km.
    #   i	II est recommande que des objectifs opérationnels soient définis en vue d'atteindre le troisième objectif de conservation (maintien de l'equilibre de I' ecosysteme ).
    #   i d	Bradford: I d like to do it myself.
    #   i m	Rep.) I m glad to see this approach.
    #   isn t	He asked, since there was an open fishery on the 4TVn cod stock in 4T, isn t there already an opportunity to collect commercial fishery information.
    #   it d	For data that are available, it d seem preferable to fit sex and age combined as part of the composition data (DM or multinomial).
    #   it s	There was discussion about the population growth rate and it s use in justifying or setting harvest levels.
    #   j	Previous analyses found that this was the optimal number to provide adequate precision (J.
    #   j ai	J ai aimé l'idée d'un processus ouvert où rien n'est caché.
    #   j aime	J aime aussi beaucoup les figures utilisées pour montrer leurs analyses de l'évaluation des modèles à l'aide de données indépendantes et dépendantes des seuils.
    #   j appelle	Quatre documents ont été mis à disposition avant la réunion d'examen (j appelle ces documents Doc1, Doc2, Doc3 et Doc4 dans mon rapport).
    #   j attends	J attends avec impatience la réunion pour pouvoir discuter davantage des hypothèses qui ont été mises à l'essai par les auteurs.
    #   j aurais	J aurais tablé sur environ 60 jours.
    #   j avais	J avais démasqué les hommes aveugles, et ils étaient tous moi.
    #   j en	Cairns : J en conviens; il y a beaucoup de suppositions qui semblent peu plausibles.
    #   j entends	Veuillez consulter ce texte pour plus de détails sur ce que j entends par pleine intégration.
    #   j espère	Cette réunion est très importante et j espère que vous pourrez y participer.
    #   j essaie	Cairns : J essaie de faire concorder le moment de l'effet prédit par l'hypothèse avec la réaction au barrage de Moses-Saunders pour commencer à démêler ces éléments.
    #   j imagine	La productivité augmente pour compenser, j imagine.
    #   j étais	J étais heureux de constater que le modèle n'est pas particulièrement sensible à ces choix.
    #   k	Adjusting for the relative catchability of all species to the groundfish trawl survey indicates an increase in total biomass and a system that is currently strongly dominated by small pelagic biomass (K.
    #   l	Ces variations sont attribuées à deux facteurs principaux : 1) les interactions avec l'atmosphère (l échange de chaleur entre l'eau et l'air, les précipitations, l'évaporation, la formation de glace), et 2) les masses d'eau qui se déplacent entre le Golfe et l'océan Atlantique par les détroits de Cabot et de Belle Isle (fig.
    #   l a	Pour cette raison, L' a été définit arbitrairement comme étant la longueur, sur la courbe des captures cumulatives, où au moins 25 des capelans sont capturés.
    #   l amour	Quatre de ces espèces (l amour blanc, la carpe à grosse tête, la carpe argentée et la carpe noire) ont été introduites dans tous les coins du monde aux fins d'aquaculture.
    #   l avait	De plus, des résultats similaires aux deux premières techniques seraient produits dans le cas de l'équation de Beverton et Holt si le choix de L' avait porté sur la longueur, sur une courbe des captures cumulatives, où environ 30 des capelans sont capturés.
    #   l est	34 iv RÉSUMÉ L'état du contingent nord du maquereau de l'Atlantique Nord-Ouest (Scomber scombrus L.) est évalué tous les deux ans à l'aide d'un modèle d'évaluation des stocks structuré selon l'âge qui tient explicitement compte des statistiques sur les prises manquantes des flottilles canadiennes et américaines.
    #   l un	Il n'a pas été possible de déterminer la parenté des cinq autres juvéniles de la rivière Salmon (l un d'eux avait trop peu de loci pour pouvoir faire la distinction entre plusieurs parents possibles).
    #   let s	So let s assume that recovery is possible and we know that it is taken by food fisheries (mixed species, but are directed towards chub) and in recreational fisheries.
    #   m	At the surface, the range is about 16 C but there is little or no seasonal change at depths greater than approximately 150 to 200 m.
    #   m a	La mortalité naturelle (M) a été élevée (proche de 0,4), mais elle semble diminuer.
    #   m en	On discute brièvement de certains des facteurs biologiques et environnementaux qui pourraient avoir une incidence sur M, en indiquant que les conditions se sont améliorées récemment; toutefois, on ne sait pas trop comment l'environnement a influé sur M.
    #   m est	Un participant demande quel taux de mortalité naturelle (M) est utilisé.
    #   m ont	À l'intérieur d'une période d'un mois (à l'hiver), les masses d'eaux profondes (mesurées à 160 m) ont subi de fortes 4 variations de température, passant de 1,7 C à 4,8 C.
    #   m y	Le programme prélève des échantillons jusqu à des profondeurs de 2 500 m, y compris à certains emplacements au- dessus ou à proximité de monts sous-marins.
    #   n	Since the presence of N.
    #   n a	Boone: Lorsque le problème de l'indice larvaire s'est pose, les scientifiques ont fait des releves acoustiques, mais rien n'' a ete prouve jusqu'a maintenant.
    #   n en	Chaque graphique comprend l'année (en caractères gras, en haut à gauche) et la taille de l'échantillon (N, en haut à droite), et la ligne horizontale en pointillés indique la proportion minimale requise pour éviter la compression de la queue.
    #   n est	La probabilité d'exposition repose sur un processus binomial qui suppose que la probabilité de réussite (P) d'un essai individuel (année) est de 0,6875 et que le nombre d'essais (n) est de huit.
    #   n importe	Nous distinguons la base biologique d'un dommage grave (n importe quelle UC ayant un état rouge) de la probabilité que cela se produise, ce qui implique de prendre une décision sur la tolérance au risque.
    #   o	Le banc Georges devrait être inclus dans les scénarios de la taille maximum pour le calcul de O R.
    #   p	En général, toutefois, la biomasse était à son plus fort dans les bassins profonds et dans les eaux profondes du large du plateau, ou dans les chenaux (p.
    #   q	Q- Why were females becoming mature at a smaller size in recent years.
    #   r	R- Ce phénomène pourrait indiquer que ce secteur bénéficie d'un meilleur recrutement.
    #   s	All of the hydrographic data are edited and archived in Canada s national Marine Environmental Data Service (MEDS) database.
    #   s T	Detailed studies on macrophytes have been conducted in some Arctic regions (e.g., Stefansson S s T occur.
    #   s agit	II s' agit la d' une question de biodiversité.
    #   s en	Le temps passé (s) en phase de remontée et de descente a été calculé comme étant la distance parcourue (m), divisée par la vitesse de nage (m s) pour chaque phase, où la distance parcourue est égale à la profondeur de plongée (m) corrigée en fonction du tangage moyen ( ).
    #   s est	Le taux de recrutement (R S) est jugé un indice adéquat mais l'utilisation de ce paramètre soulève aussi beaucoup de questions.
    #   s il	Deux questions posées pour stimuler la discussion sur le concept de projet sentinelle : - quels sont les changements (s il y a lieu) aux concepts qui pourraient être adoptés maintenant ou dans le futur, tenant compte que tout changement pourrait avoir un effet sur les séries de données établies et sur les évaluations en général.
    #   s ils	On ne sait pas si les baleines peuvent réduire les effets de masquage par divers moyens, comme des changements dans leurs patrons de vocalisation, et les conséquences de ces changements (s ils se produisent) sont inconnues.
    #   s it	At the estimated propagation speeds of 65 m s, it takes roughly 10 to 15 minutes for the simulated waves to propagate the roughly 40 to 45 km to the intersection of Douglas Channel and Kitimat Arm, where peak wave amplitudes would be diminished to less than 1 m.
    #   s s	The full model specification is, therefore: Ys s, g( s) xs T s s, s N(0, 2), s GP(0, C(s, s ; )).
    #   s that	In previous assessments, this model was presented without a cubic length term, resulting in predicted F s that were distinctly dome-shaped across the range of lengths.
    #   s there	Description of Fisherie s There are no TACs for the Canadian Atlantic dogfish fishery.
    #   s where	The five cyclic CU s where new Larkin-based abundance benchmarks applied included the following: Takla- Trembleur-Early Stuart, Shuswap-ES, Takla-Trembleur-Stuart-S, Quesnel-S, Shuswap Complex-L.
    #   s était	Dans cette couche, la vitesse du courant maximale la plus faible (environ 14 cm s) était enregistrée à la station BB001, qui se trouve dans une anse abritée de Belle Bay.
    #   shouldn t	A fisher felt that shrimp liners shouldn t be used; they affect the efficiency of the nets.
    #   t	Une réduction de 50 du F relatif serait un objectif raisonnable, mais signifie des débarquements de seulement 1 000 t.
    #   t a	La température moyenne des dix premiers mètres (T) a été utilisée pour calculer le temps d'incubation total (T;J.
    #   t can	The difference, of approximately 360 t, can be attributed to slightly different analytical approaches mainly the variogram and neighboring of the kriging points.
    #   t elle	La biomasse chalutable de 4X a baissé; de plus de 8 000 t, elle a chuté bien au-dessous de 1 000 t'à l'heure actuelle.
    #   t en	Les estimations de la biomasse en 2J s'élevaient à 4 760 t'(4 596 -4 924 t), dont 771 t'(758-784 t) en 3L (surtout des poissons de 35 cm et immatures ou matures; les zones ciblées en 3L n'ont pas été sondées en totalité).
    #   t est	Le temps de génération (T) est le temps en années pendant lequel la population augmente d'un facteur R0.
    #   t il	Comme la BSR combinée des composants côtier et extracôtier demeure inférieure au niveau repère de 150 000 t, il n'est pas nécessaire de résoudre la question à la présente réunion.
    #   t it	With 150 t, it will provide a better idea of crab distribution on the sea floor because fishermen will be spread out across the entire area.
    #   t on	Lorsque la biomasse de reproducteurs de l'ensemble du stock de morue de 2J3KL s'approchera de 150 000 t, on examinera les données disponibles pour établir des points de référence limites pour la biomasse des reproducteurs, conformément à l'approche de précaution.
    #   t ont	Nous avons estimé la biomasse exploitable dans trois secteurs de 3KL et 3Ps pendant les semaines où des débarquements suffisants ( 100 t) ont été déclarés afin d'obtenir des estimations raisonnables.
    #   t t	The model formulation is identical to the spatial case: Yt t, g( t) xt T t t, t N(0, 2), t GP(0, C(t, t ; )).
    #   t t,	The model formulation is identical to the spatial case: Yt t, g( t) xt T t t, t N(0, 2), t GP(0, C(t, t ; )).
    #   that s	That s what really matters for the survival of the larvae.
    #   that t	These two observations support the hypothesis that T.
    #   there s	There s a possibility of recruitment between the survey and the fishery.
    #   u	A la réunion, le personnel des sciences donnera un bref aper u de ses evaluations, soit les principales conclusions, les preuves a l'appui, les nouvelles methodes et les principales contraintes.
    #   v	individuals of a species are widespread and even areas of comparatively high density do not contain a substantial portion of the total population; OR v.
    #   w	Migration Lo w The migration is carried out using several routes, which are chosen indiscriminately.
    #   wasn t	The length of the time series for Gulf boats implies that learning probably wasn t biasing the data.
    #   weren t	They did try to look at whether certain age classes weren t well represented, but this would be difficult now because in recent years it is not possible to even land on the ice to collect such data due to its poor quality.
    #   what s	The document insights all kinds of potential responses, but what s in the document might give us enough info to go through our checklist.
    #   where s	Ws sLs s (C.2) where s and s are the parameters of the equation specifc to sex, and Ls and Ws are paired length (L) and weight (W ) observations from synoptic surveys (Tables C.1 and C.2).
    #   won t	But we need to document what we feel is needed to do this job right and then communicate what we won t be able to do.
    #   wouldn t	Also given that fishery was mainly by line gear, wouldn t we expect fish to be smaller.
    #   x	Satellite data are available at resolution of 18km X 18km.
    #   y	Truly long-term study (30 y) at the scale of the fishery.
    #   you d	Comment: Put opinions on first and second priorities in the assessment as two indices, but you d also have to include the age groups because, for example, the longlines pick up a pulse of fish before the gillnets.
    #   z	Z is very high: is it M or F.
    #   á	Á un taux d'exploitation fixe de 0,3 ou moins et pour toutes les politiques basées sur l'abondance, la différence dans les taux d'échec de conservation était beaucoup plus grande dans le contexte d'un taux de survie en mer élevé.
    #   â	On convertit ensuite â de grammes en kilotonnes à l'aide des facteurs de conversion appropriés; au besoin, on peut l'additionner entre les classes d'âge et les strates pour obtenir la biomasse annuelle selon l'âge, la biomasse annuelle ou la biomasse de la strate.
    #   é	Il est également nécessaire d'examiner à l'avance la façon dont les objectifs opérationnels permettront de faciliter la gestion des impacts cumulatifs ou Des objectifs écosystém é écosystèmes.
    #   î	Sélection du modèle pour les indices d'abondance dépendants de la pêche en Nouvelle-Écosse (N.-É.) et à l'Île-du-Prince-Édouard (Î.- P.-É.) au moyen d'un modèle linéaire généralisé (MLG) binomial négatif (BN).
    #   ø	http: www.isdm-gdsi.gc.ca csas-sccs applications events-evenements index-eng.asp http: www.isdm-gdsi.gc.ca csas-sccs applications events-evenements index-eng.asp National Capital Region Risk Assessments of EO-1 Salmon 29 Aas, Ø., Einum, S., Klemetsen, A., and Skurdal, J.
