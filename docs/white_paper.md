---
title: "Bordeaux Multi-Asset Lab"
subtitle: "Un framework systématique d'allocation tactique multi-actifs guidé par le régime macroéconomique"
author: "TTB10"
date: "Mai 2026"
abstract: |
  Nous présentons un framework systématique d'allocation tactique multi-actifs construit sur le principe d'identification de régimes macroéconomiques. Le système classifie l'environnement courant parmi cinq régimes définis par le croisement des dimensions croissance et inflation, en s'appuyant sur six indicateurs publics extraits de la base FRED de la Réserve fédérale de Saint-Louis. Pour chaque régime, une allocation cible par classe d'actifs est calibrée à partir d'un portefeuille de référence 60/40 enrichi multi-actifs, avec des tilts modérés inspirés du framework All Weather de Bridgewater. Un mécanisme de lissage par confidence assure que l'allocation finale ne s'écarte de la référence neutre que dans la mesure où le signal est statistiquement crédible. Les fonds concrets sont ensuite sélectionnés au sein d'un univers de 49 ETFs UCITS européens via un scoring composite Sharpe-drawdown-frais. Le portefeuille résultant produit, sur trois années glissantes (mai 2023 - mai 2026), une performance annualisée de 25.67 % contre 21.06 % pour le benchmark 60/40 standard, avec une volatilité comparable et un Sharpe ratio supérieur de 0.7 unité. Nous discutons les limites de cette validation préliminaire, identifions les axes d'amélioration prioritaires (backtest pluriannuel, modélisation des coûts de transaction, élargissement géographique des indicateurs), et présentons la roadmap d'évolution du système.

  **Mots-clés** : allocation tactique, régimes macroéconomiques, risk parity, multi-asset, sélection de fonds, ETF UCITS.
geometry: margin=2.2cm
fontsize: 11pt
colorlinks: true
linkcolor: "blue"
urlcolor: "blue"
toc: true
toc-depth: 2
numbersections: true
---

\newpage

# Résumé exécutif

L'allocation d'actifs est, selon plusieurs études classiques [@Brinson1986 ; @Ibbotson2000], le déterminant majeur de la performance d'un portefeuille à long terme, devant la sélection de titres et le timing de marché. Pourtant, l'allocation tactique systématique reste relativement peu accessible au gérant indépendant ou à l'investisseur particulier sophistiqué, qui dépend généralement soit d'allocations passives statiques (60/40), soit de mandats discrétionnaires opaques.

Ce document présente *Bordeaux Multi-Asset Lab*, un framework open-source d'allocation tactique multi-actifs développé en Python. Le système poursuit trois objectifs : produire une allocation tactique défendable à partir de données publiques, maintenir la transparence et la traçabilité de chaque décision, et s'inscrire dans une discipline de publication mensuelle vérifiable.

L'approche méthodologique combine quatre briques distinctes :

1. **Une classification de régime** parmi cinq états (Goldilocks, Reflation, Récession désinflationniste, Stagflation, Incertain) déterminés par le croisement des dimensions croissance et inflation, suivant un cadre conceptuel popularisé par Bridgewater Associates [@Dalio2017].

2. **Une table de tilts modérés par régime**, calibrés autour d'une allocation neutre 60/40 enrichie multi-actifs, avec des écarts maximaux de plus ou moins 15 % par classe d'actifs.

3. **Un mécanisme de régularisation par confidence**, qui interpole linéairement entre l'allocation neutre et le tilt cible, assurant que la prise de risque tactique est proportionnelle à la qualité du signal.

4. **Une sélection systématique d'ETFs** au sein d'un univers UCITS de 49 lignes, par scoring composite combinant ratio de Sharpe à 3 ans (60 %), drawdown maximal (25 %) et frais courants (15 %).

Sur la période mai 2023 - mai 2026, la simulation indique une surperformance annualisée de 4.6 points par rapport à un benchmark 60/40 standard (CSPX.L à 60 %, IB01.L à 40 %), avec une volatilité comparable. Le ratio de Sharpe simulé atteint 3.23 contre 2.53 pour le benchmark, et le beta du portefeuille s'établit à 0.86, suggérant un profil légèrement défensif.

Nous discutons en section 6 les limites majeures de cette validation préliminaire — au premier rang desquelles l'absence de backtest pluriannuel et le poids dominant de la diversification multi-actifs et de la sélection intra-poche dans la surperformance observée. Le timing macroéconomique proprement dit n'a pas eu l'opportunité de jouer pleinement sur cette fenêtre, le régime détecté en mai 2026 étant *Incertain* avec une confidence de 6 %, ce qui place l'allocation à 95 % alignée sur la référence neutre.

Le code source, les données de configuration, et les résultats sont accessibles publiquement à l'adresse `https://github.com/TTB10/bordeaux-multi-asset-lab`.

\newpage

# Introduction

## Contexte et motivation

L'allocation tactique d'actifs (TAA) regroupe l'ensemble des techniques visant à ajuster dynamiquement la pondération des classes d'actifs d'un portefeuille en fonction des conditions de marché anticipées. Elle s'oppose à l'allocation stratégique, qui maintient des pondérations stables à long terme, et à la sélection de titres, qui opère au sein d'une classe d'actifs donnée.

La littérature académique sur la TAA est ancienne et abondante. Faber [@Faber2007] a popularisé une approche purement quantitative basée sur la moyenne mobile à 10 mois, démontrant qu'une simple règle de timing de marché pouvait améliorer significativement le ratio rendement-risque par rapport à un buy-and-hold. Plus récemment, les travaux d'Asness, Frazzini et Pedersen [@AsnessFrazziniPedersen2012] sur le risk parity, ou les publications publiques de Bridgewater Associates sur l'All Weather Strategy, ont contribué à formaliser l'idée qu'un portefeuille équilibré sur le risque (et non sur le capital) bénéficie de propriétés défensives supérieures à un 60/40 traditionnel.

Sur le plan opérationnel néanmoins, la TAA systématique demeure peu accessible. Les boutiques de gestion patrimoniale fonctionnent majoritairement en discrétionnaire, exposant leurs clients à un risque de modèle et à une opacité méthodologique. Les robo-advisors grand public (Yomoni, Nalo, Trade Republic) appliquent généralement une allocation strategic statique selon un profil de risque, sans réelle adaptation à l'environnement macro. Quant aux fonds quanti institutionnels, ils restent inaccessibles à la majorité des investisseurs particuliers.

L'émergence des ETFs UCITS européens, les plateformes API gratuites comme la base FRED de la Réserve fédérale de Saint-Louis, et la montée en compétences Python parmi les jeunes professionnels de la finance créent toutefois les conditions pour qu'un cadre systématique transparent puisse être développé et défendu publiquement.

## Objectifs du projet

Le projet *Bordeaux Multi-Asset Lab* poursuit quatre objectifs explicites :

1. **Reproductibilité totale**. Toutes les données utilisées sont publiques (Yahoo Finance, FRED), tout le code est open-source, et chaque décision méthodologique est documentée. Un tiers doit pouvoir reproduire à l'identique l'ensemble des résultats à partir du dépôt GitHub.

2. **Robustesse opérationnelle**. Le système doit fonctionner de manière fiable malgré les pannes occasionnelles des API externes. Cela inclut un mécanisme de retry-and-backoff, des tests unitaires couvrant 90 % du code, et une intégration continue qui bloque tout merge cassant.

3. **Honnêteté intellectuelle**. Le système doit refuser d'émettre des paris directionnels lorsque les signaux sont contradictoires ou faibles. Le mécanisme de smoothing par confidence formalise cette discipline : l'allocation finale ne s'écarte du benchmark neutre que dans la mesure où la conviction macro est statistiquement justifiée.

4. **Discipline de publication mensuelle**. À partir du 5 juillet 2026, une lettre d'investissement mensuelle sera publiée, présentant le régime détecté, l'allocation cible, le portefeuille concret, et la performance écoulée. Cette régularité construit un track record vérifiable et impose une discipline de revue continue du framework.

## Contributions

Ce document présente quatre contributions principales :

- **Une architecture modulaire** en sept composants stricts (data, universe, regime, allocation, selection, risk, portfolio), illustrant l'application du pattern Stratégie de la conception orientée objet à un domaine de finance quantitative. Chaque module est testable indépendamment et substituable derrière son interface.

- **Un mécanisme de régularisation par confidence** qui formalise l'idée intuitive selon laquelle l'amplitude des paris tactiques doit être proportionnelle à la qualité du signal. Nous montrons en section 4.3.3 que cette régularisation est mathématiquement équivalente à un mélange convexe entre allocation neutre et allocation cible.

- **Une calibration de tilts modérés** inspirée du framework All Weather, mais limitée à des écarts de plus ou moins 15 % par classe d'actifs vis-à-vis de la référence neutre. Nous justifions ce choix en section 4.3.2 par la stabilité des allocations résultantes et la défendabilité publique du framework.

- **Un scoring composite de fonds** combinant ratio de Sharpe, résilience en drawdown et frais courants, normalisé par z-score au sein de chaque peer group. Ce scoring sépare proprement la qualité intrinsèque du fonds (Sharpe), la résilience au stress (drawdown), et le coût (frais).

## Plan du document

La section 3 présente une revue de la littérature pertinente. La section 4 détaille la méthodologie complète, depuis le choix des indicateurs macroéconomiques jusqu'à la construction du portefeuille final. La section 5 présente les résultats empiriques sur la période mai 2023 - mai 2026, avec une comparaison systématique au benchmark 60/40. La section 6 discute les forces et limites du framework, et identifie les axes prioritaires d'amélioration. La section 7 conclut et présente la feuille de route d'évolution.

\newpage

# Revue de littérature

## Allocation tactique multi-actifs

L'idée que l'allocation d'actifs domine la sélection individuelle de titres dans la formation de la performance à long terme remonte aux travaux fondateurs de Brinson, Hood et Beebower [@Brinson1986], qui établissent que près de 90 % de la variance des rendements d'un portefeuille est expliquée par sa politique d'allocation, et non par les décisions de market timing ou de stock picking. Ces résultats ont été contestés et raffinés par Ibbotson et Kaplan [@Ibbotson2000], qui distinguent la part de la variance expliquée *au sein* d'un portefeuille (90 %) de la part expliquée *entre* portefeuilles (40 %), mais le message central demeure : la décision d'allocation est de premier ordre.

Faber [@Faber2007] propose une règle simple de timing tactique basée sur la moyenne mobile à 10 mois : allouer à une classe d'actifs si son cours est au-dessus de sa moyenne mobile, basculer en cash sinon. Sur 35 ans de données américaines, cette règle simple améliore le Sharpe de l'allocation buy-and-hold tout en réduisant significativement le drawdown maximal. Le succès empirique de Faber a contribué à légitimer les approches systématiques règle-based en allocation tactique.

## Détection de régimes macroéconomiques

L'identification de régimes macroéconomiques distincts comme guide à l'allocation est une idée ancienne. Hamilton [@Hamilton1989] formalise l'approche par chaînes de Markov cachées (Hidden Markov Models), démontrant que les cycles économiques peuvent être modélisés comme des transitions probabilistes entre régimes latents. Ang et Bekaert [@AngBekaert2002] appliquent cette approche à l'allocation internationale et démontrent l'existence de deux régimes distincts (calme vs crise) dans les corrélations entre marchés.

Pour la prédiction des récessions américaines, Estrella et Mishkin [@EstrellaMishkin1998] établissent l'efficacité de l'écart de taux entre Treasury 10 ans et 3 mois (`T10Y3M`) comme indicateur avancé. Cette série, disponible sur la base FRED, est devenue un standard dans la littérature sur les régimes macro et figure dans notre framework comme l'un des trois indicateurs de la dimension croissance.

L'approche pragmatique du « 2x2 macro framework » a été popularisée par Ray Dalio dans ses publications publiques sur l'All Weather Strategy de Bridgewater [@Dalio2017]. Dalio postule l'existence de quatre environnements macroéconomiques fondamentaux résultant du croisement des dimensions croissance et inflation, chacun favorisant des classes d'actifs spécifiques. Notre framework adopte cette structure conceptuelle, étendue d'un cinquième état (« Incertain ») qui formalise le refus de classifier lorsque les signaux sont contradictoires.

## Risk parity et All Weather

Le framework All Weather de Bridgewater repose sur le principe de la parité de risque (risk parity), formalisé académiquement par Asness, Frazzini et Pedersen [@AsnessFrazziniPedersen2012]. L'idée centrale est qu'un portefeuille où chaque classe d'actifs contribue de manière égale au risque total (et non au capital total) bénéficie d'un meilleur ratio rendement-risque qu'un portefeuille équilibré en capital. En pratique, cela conduit à des allocations qui surpondèrent les obligations longues et les actifs réels (or, commodities) par rapport à un 60/40 traditionnel.

Le risk parity strict requiert toutefois l'usage de levier pour atteindre le profil de rendement souhaité, ce qui ne convient pas à tous les contextes (notamment les UCITS retail). Notre framework adopte une approche pragmatique : il s'inspire de la structure tilts par régime de Bridgewater, mais sans recourir au levier, et avec une contrainte explicite de modération des écarts vis-à-vis du 60/40 enrichi.

## Sélection de fonds quantitative

La sélection systématique de fonds (fund selection) repose sur la combinaison de critères de performance ajustée du risque, de résilience au stress, et de coût. Sharpe [@Sharpe1966] introduit le ratio qui porte son nom comme mesure de performance ajustée du risque, défini comme l'excès de rendement par unité de volatilité. Sortino et Price [@SortinoPrice1994] proposent une variante utilisant uniquement la volatilité « downside » (calculée sur les rendements négatifs), plus rigoureuse théoriquement pour des distributions asymétriques.

Le ratio de Sharpe seul reste insuffisant pour la sélection de fonds car il peut masquer des périodes de forte perte ponctuelle (« tail risk »). C'est pourquoi nous complétons systématiquement le Sharpe par le maximum drawdown, qui capture la pire chute peak-to-trough observée sur la période. Calmar [@Young1991] propose le ratio rendement annuel divisé par drawdown maximal absolu comme mesure synthétique, mais cette métrique, très dépendante d'événements ponctuels, est moins adaptée à un scoring continu.

Pour les frais courants (Total Expense Ratio, TER), de nombreuses études [@Carhart1997 notamment] établissent qu'ils constituent un prédicteur statistiquement significatif (et négatif) de la performance future nette des fonds. Cela justifie leur inclusion dans le scoring, avec un poids modéré (15 %) reflétant le fait qu'à Sharpe et drawdown comparables, le fonds le moins cher est préférable.

\newpage

# Méthodologie

Cette section présente le framework dans son intégralité, depuis l'acquisition des données jusqu'à la construction finale du portefeuille. Chaque sous-section détaille les choix méthodologiques et leur justification.

## Architecture conceptuelle

Le framework est structuré en sept modules distincts, chacun avec une responsabilité unique et une interface stable. Cette modularité, inspirée des principes SOLID de la conception orientée objet [@Martin2017], permet la substitution indépendante de chaque composant et facilite les tests unitaires.

| Module | Responsabilité |
|---|---|
| `data` | Acquisition des séries de prix (Yahoo Finance) et macroéconomiques (FRED), avec retry-and-backoff |
| `universe` | Chargement de l'univers d'investissement depuis configuration YAML versionnée |
| `regime` | Transformation de 6 lectures macro en classification parmi 5 régimes, avec confidence |
| `allocation` | Mapping régime → allocation cible par classe d'actifs, avec smoothing |
| `selection` | Sélection des fonds concrets dans chaque poche, par scoring composite |
| `portfolio` | Maintien de l'état temporel du portefeuille avec persistance JSON |
| `risk` | Calcul des métriques empiriques de risque |

Le pipeline de production exécute ces modules en séquence linéaire : `data + universe → regime → allocation → selection → portfolio + risk`. Chaque transition produit un artefact validé (modèle Pydantic frozen) qui constitue l'entrée du module suivant.

## Détection de régime

### Choix des indicateurs

Le framework utilise six indicateurs macroéconomiques publics, tous disponibles sur la base FRED de la Réserve fédérale de Saint-Louis. Trois indicateurs sont attribués à la dimension Croissance, trois à la dimension Inflation. Le tableau 1 résume ce choix.

**Tableau 1 — Indicateurs macroéconomiques utilisés**

| Code FRED | Nom | Dimension | Mesure | Fréquence |
|---|---|---|---|---|
| `T10Y3M` | Yield curve 10y3m | Croissance | Écart Treasury 10y - 3m | Quotidienne |
| `INDPRO` | Industrial Production | Croissance | Indice de production industrielle (transformé en YoY %) | Mensuelle |
| `ICSA` | Initial Jobless Claims | Croissance | Demandes hebdomadaires d'allocations chômage (MA 4 semaines, signe inversé) | Hebdomadaire |
| `T5YIFR` | 5y5y Forward Inflation | Inflation | Anticipations d'inflation 5-10 ans dérivées des TIPS | Quotidienne |
| `CPILFESL` | Core CPI | Inflation | Indice des prix à la consommation hors énergie/alimentation (transformé en YoY %) | Mensuelle |
| `DCOILWTICO` | WTI Oil Momentum | Inflation | Prix WTI (transformé en momentum 6 mois) | Quotidienne |

Le choix de ces six indicateurs résulte d'un arbitrage entre richesse du signal et parcimonie. Trois indicateurs par dimension permettent une agrégation par vote majoritaire qui demeure résistante à la défaillance d'un indicateur individuel. Au-delà de trois, le gain marginal de précision diminue rapidement et le risque d'introduire des indicateurs corrélés (qui ne contribuent pas indépendamment à l'information) augmente.

L'indicateur `T10Y3M` est documenté comme indicateur avancé de récession depuis [@EstrellaMishkin1998]. L'indicateur `INDPRO` complète cette information de marché par un signal d'économie réelle, et `ICSA` apporte une lecture précoce du marché du travail. Sur la dimension inflation, `T5YIFR` reflète les anticipations de marché, `CPILFESL` mesure l'inflation réalisée, et `DCOILWTICO` constitue l'unique indicateur véritablement forward-looking via le pass-through pétrolier dans le headline CPI.

L'absence d'indicateurs européens, asiatiques ou émergents constitue une limite explicite que nous discutons en section 6.2.

### Normalisation par z-score

Chaque indicateur est transformé en un z-score sur fenêtre glissante de cinq ans :

$$z_t = \frac{x_t - \mu_t^{(5y)}}{\sigma_t^{(5y)}}$$

où $\mu_t^{(5y)}$ et $\sigma_t^{(5y)}$ désignent respectivement la moyenne et l'écart-type empiriques de la série $x$ calculés sur les 1260 derniers jours ouvrés (équivalent de cinq années de trading).

Le choix de la fenêtre à cinq ans résulte d'un compromis. Une fenêtre plus longue (par exemple, l'historique complet depuis 1996) produit des estimations plus stables mais aveugles aux changements de régime structurels comme la baisse séculaire des taux entre 2008 et 2020. Une fenêtre plus courte (par exemple, deux ans) capture mieux les changements récents mais est plus volatile et tend à donner des z-scores élevés dès qu'un indicateur sort du couloir étroit. Cinq ans correspond approximativement à la durée typique d'un cycle économique élargi.

À partir du z-score, une direction discrète est attribuée selon des seuils :

$$d_t = \begin{cases} \text{UP} & \text{si } z_t > +0.5 \\ \text{DOWN} & \text{si } z_t < -0.5 \\ \text{NEUTRAL} & \text{sinon} \end{cases}$$

La confidence individuelle de chaque indicateur est définie comme :

$$c_t = \min\left(\frac{|z_t|}{2}, 1\right)$$

Cette spécification garantit que la confidence est bornée dans [0, 1], qu'elle est nulle au point neutre, et qu'elle plafonne à partir d'un z-score de 2 (les valeurs extrêmes au-delà ne sont pas plus informatives).

### Agrégation par dimension

Pour chaque dimension (Croissance, Inflation), les trois indicateurs sont agrégés en un signal directionnel synthétique par vote pondéré par la confidence :

$$\text{score} = \frac{\sum_i \text{contribution}_i \times c_i}{\sum_i c_i}$$

où $\text{contribution}_i = +1$ si $d_i = \text{UP}$, $-1$ si $d_i = \text{DOWN}$, et $0$ si $d_i = \text{NEUTRAL}$. Le score résultant est dans l'intervalle [-1, +1].

La direction agrégée de la dimension est déterminée selon le seuil :

$$D = \begin{cases} \text{UP} & \text{si score} > +0.3 \\ \text{DOWN} & \text{si score} < -0.3 \\ \text{NEUTRAL} & \text{sinon} \end{cases}$$

La confidence agrégée de la dimension est calculée selon une formule qui combine la cohérence directionnelle et la qualité moyenne du signal :

$$C = |\text{score}| \times \frac{1}{n}\sum_i c_i$$

où $n$ est le nombre d'indicateurs contribuant à la dimension. Cette formule pénalise simultanément la divergence directionnelle (via $|\text{score}|$) et la faiblesse intrinsèque des indicateurs (via la moyenne des confidences). Elle évite notamment le biais d'une confidence affichée maximale lorsqu'un seul indicateur peu fiable est dans une direction donnée.

### Classification du régime

Le régime macroéconomique est classifié à partir du croisement des directions des deux dimensions, selon le tableau 2.

**Tableau 2 — Classification des régimes**

| | Inflation DOWN | Inflation UP | Inflation NEUTRAL |
|---|---|---|---|
| **Croissance UP** | Goldilocks | Reflation | Incertain |
| **Croissance DOWN** | Récession désinflationniste | Stagflation | Incertain |
| **Croissance NEUTRAL** | Incertain | Incertain | Incertain |

L'introduction explicite d'un état « Incertain » constitue une différence notable vis-à-vis du framework Bridgewater original, qui force toujours la classification dans l'un des quatre quadrants. Notre choix s'inscrit dans la philosophie de honnêteté intellectuelle énoncée en introduction : lorsque les signaux sont contradictoires, le système doit refuser de classifier plutôt que de produire un faux signal.

La confidence du régime est définie de manière conservatrice :

$$C_{\text{regime}} = \min(C_{\text{growth}}, C_{\text{inflation}})$$

Le rationnel est qu'un régime ne peut être plus fiable que sa dimension la moins fiable. Cette spécification empêche une dimension forte de masquer la fragilité de l'autre.

## Allocation stratégique

### Allocation neutre 60/40 enrichie

L'allocation de référence (« neutre ») est un 60/40 multi-actifs enrichi, dont la composition est présentée dans le tableau 3. Cette allocation est utilisée à deux titres : elle constitue la cible par défaut en régime Incertain, et elle sert de point d'ancrage pour le mécanisme de smoothing décrit en 4.3.3.

**Tableau 3 — Allocation neutre de référence**

| Classe d'actifs | Poids |
|---|---:|
| Actions développées (DM) | 40 % |
| Actions émergentes (EM) | 10 % |
| Obligations souveraines | 20 % |
| Crédit Investment Grade | 10 % |
| Crédit High Yield | 5 % |
| Or | 5 % |
| Foncier coté | 5 % |
| Cash / monétaire | 5 % |
| **Total** | **100 %** |

Cette allocation s'écarte d'un 60/40 traditionnel (60 % actions, 40 % obligations) par l'inclusion modérée d'actifs réels (or, foncier coté) et de crédit, et par la diversification géographique des actions (50 % DM développées, 10 % émergentes). Cette structure est cohérente avec les recommandations de gestion patrimoniale équilibrée pour un horizon long.

### Tilts par régime

À chaque régime non-Incertain est associée une table de tilts, présentée dans le tableau 4. Ces tilts définissent l'allocation cible si la confidence du régime atteint 100 %.

**Tableau 4 — Tilts d'allocation par régime (en % du portefeuille)**

| Classe d'actifs | Neutre | Goldilocks | Reflation | Récession | Stagflation |
|---|---:|---:|---:|---:|---:|
| Actions DM | 40 | 50 | 35 | 25 | 25 |
| Actions EM | 10 | 10 | 10 | 5 | 5 |
| Obligations souveraines | 20 | 15 | 10 | 35 | 15 |
| Crédit IG | 10 | 10 | 5 | 15 | 5 |
| Crédit HY | 5 | 5 | 5 | 0 | 0 |
| Or | 5 | 0 | 10 | 5 | 15 |
| Matières premières | 0 | 0 | 10 | 0 | 15 |
| Foncier coté | 5 | 5 | 10 | 0 | 5 |
| Cash | 5 | 5 | 5 | 15 | 15 |
| **Total** | **100** | **100** | **100** | **100** | **100** |

Trois principes guident la calibration de ces tilts :

1. **Modération**. Aucun tilt n'écarte plus de 15 points une classe d'actifs vis-à-vis de l'allocation neutre. Cette contrainte évite les paris extrêmes peu défendables et reflète la pratique des gérants multi-actifs professionnels.

2. **Cohérence théorique**. Les tilts respectent la logique conceptuelle de chaque régime. Goldilocks (croissance UP, inflation DOWN) favorise les actifs risqués, Reflation introduit de l'inflation hedging via or et matières premières, Récession charge les actifs défensifs (souverain long, cash, IG), Stagflation maximise les actifs réels et minimise actions et obligations.

3. **Sommabilité parfaite**. Chaque colonne du tableau somme exactement à 100 %, ce qui garantit que toute interpolation entre l'allocation neutre et un tilt cible donne une allocation valide.

### Mécanisme de smoothing par confidence

L'allocation finale est obtenue par interpolation linéaire entre l'allocation neutre et le tilt du régime détecté, pondérée par la confidence :

$$w_{i}^{*} = w_{i}^{\text{neutre}} + C_{\text{regime}} \times (w_{i}^{\text{regime}} - w_{i}^{\text{neutre}})$$

où $w_{i}^{\text{neutre}}$ est le poids neutre de la classe d'actifs $i$, $w_{i}^{\text{regime}}$ est son poids cible dans le régime détecté, et $C_{\text{regime}} \in [0, 1]$ est la confidence du régime.

Cette spécification possède plusieurs propriétés désirables :

- **Stabilité aux signaux faibles**. Lorsque $C_{\text{regime}} \to 0$, l'allocation tend vers la référence neutre. Le système refuse d'engager du capital sur la base d'une conviction insuffisante.
- **Linéarité**. La transformation est continue et monotone en $C_{\text{regime}}$, garantissant que des changements progressifs du signal produisent des changements progressifs de l'allocation.
- **Préservation de la sommabilité**. Si $\sum_i w_{i}^{\text{neutre}} = \sum_i w_{i}^{\text{regime}} = 1$, alors $\sum_i w_{i}^{*} = 1$ pour tout $C_{\text{regime}}$. La preuve est immédiate par linéarité de la sommation.

En régime Incertain, le système court-circuite cette interpolation et retourne directement l'allocation neutre, indépendamment de la confidence (qui est de toute façon faible par construction).

## Sélection de fonds

### Univers d'investissement

L'univers de sélection comprend 49 ETFs UCITS européens, sélectionnés pour couvrir l'ensemble des classes d'actifs du framework et pour leur liquidité, leur taille (encours), et la qualité de leur tracking. La liste complète figure en annexe A. La répartition par classe d'actifs est résumée dans le tableau 5.

**Tableau 5 — Composition de l'univers**

| Classe d'actifs | Nombre d'ETFs |
|---|---:|
| Actions développées | 16 |
| Actions émergentes | 3 |
| Obligations souveraines | 8 |
| Crédit Investment Grade | 5 |
| Crédit High Yield | 3 |
| Or | 1 |
| Argent | 1 |
| Matières premières (broad) | 2 |
| Foncier coté | 4 |
| Convertibles | 1 |
| Cash / monétaire | 3 |
| Couverture | 2 |

Cet univers est volontairement restreint et concentré sur des produits liquides, accessibles via les plateformes brokers grand public. La restriction au cadre UCITS garantit la conformité réglementaire européenne et simplifie le traitement fiscal.

### Scoring composite

Pour chaque classe d'actifs allouée à plus de 0 %, les ETFs candidats sont scorés selon une formule composite :

$$S_j = w_{S} \cdot \tilde{z}^{S}_j + w_{D} \cdot \tilde{z}^{D}_j + w_{T} \cdot \tilde{z}^{T}_j$$

où :

- $\tilde{z}^{S}_j$ est le z-score du ratio de Sharpe sur 3 ans du fonds $j$, normalisé par rapport à ses pairs de la même classe d'actifs ;
- $\tilde{z}^{D}_j$ est le z-score du drawdown maximal sur 3 ans (signe inversé pour que « moins de drawdown = mieux ») ;
- $\tilde{z}^{T}_j$ est le z-score du Total Expense Ratio (signe inversé pour que « moins cher = mieux ») ;
- $(w_{S}, w_{D}, w_{T}) = (0.60, 0.25, 0.15)$ sont les poids respectifs.

La normalisation par z-score au sein du peer group permet de comparer des métriques aux échelles différentes (le Sharpe est sans unité, le TER est en %, le drawdown est en %). Elle assure également que la classe d'actifs reste l'unité naturelle de comparaison : un fonds n'est pas pénalisé pour avoir un drawdown de 30 % si tous ses pairs ont également 30 %, en revanche il est pénalisé s'il fait 30 % alors que ses pairs font 15 %.

Le choix des poids $(0.60, 0.25, 0.15)$ reflète une priorisation théorique : le Sharpe domine, parce qu'il intègre conjointement rendement et volatilité ; le drawdown vient ensuite, parce qu'il capture le tail risk que le Sharpe peut masquer ; le TER est marginal, parce qu'à Sharpe et drawdown comparables, l'écart de frais entre ETFs UCITS modernes est typiquement de quelques points de base, donc dominé par les autres métriques.

### Construction du portefeuille

Pour chaque classe d'actifs allouée à $w_i^{*}$ %, le système sélectionne les deux fonds au plus haut score composite et les équipondère dans la poche :

$$w_{j} = \frac{w_i^{*}}{N_j}$$

où $N_j$ est le nombre de fonds sélectionnés pour la poche $j$ (typiquement 2, ou 1 si la classe d'actifs ne compte qu'un fonds dans l'univers).

L'équipondération intra-poche est un choix de simplicité : elle évite de devoir paramétrer un seuil de différenciation entre les deux fonds top-2, et elle apporte une diversification supplémentaire au sein de la classe d'actifs. Sur le plan théorique, cette diversification réduit l'exposition au risque idiosyncratique de chaque fonds (tracking error, faillite, retrait du marché) sans coût significatif.

Si une classe d'actifs allouée n'a aucun fonds disponible dans l'univers (cas hypothétique), le poids correspondant est redistribué vers la poche cash, avec un avertissement journalisé.

Le portefeuille final somme exactement à 100 % par construction. Une étape de normalisation finale absorbe les éventuels résiduels d'arrondi.

## Mesure du risque

### Métriques empiriques

Le module risk calcule sept métriques empiriques sur la série de rendements du portefeuille. Ces métriques sont toutes non-paramétriques (sans hypothèse de normalité) et reposent uniquement sur la distribution empirique des rendements observés.

**Rendement annualisé**

$$R_{\text{annual}} = \left(\prod_{t=1}^{T} (1 + r_t)\right)^{252/T} - 1$$

où $r_t$ est le rendement journalier et $T$ le nombre d'observations.

**Volatilité annualisée**

$$\sigma_{\text{annual}} = \hat{\sigma}(r) \times \sqrt{252}$$

où $\hat{\sigma}(r)$ est l'écart-type empirique des rendements journaliers.

**Ratio de Sharpe**

$$\text{Sharpe} = \frac{R_{\text{annual}} - r_f}{\sigma_{\text{annual}}}$$

avec un taux sans risque $r_f$ par défaut à 2.5 % annuel (proche de l'EUR overnight).

**Maximum drawdown**

$$\text{MaxDD} = \min_t \left(\frac{V_t}{\max_{s \leq t} V_s} - 1\right)$$

où $V_t$ est la valeur cumulée du portefeuille au temps $t$.

**Value at Risk historique 95 %**

$$\text{VaR}_{95\%} = q_{0.05}(r)$$

où $q_{0.05}$ est le 5e percentile empirique de la distribution des rendements journaliers.

**Conditional Value at Risk 95 %**

$$\text{CVaR}_{95\%} = \mathbb{E}[r | r \leq \text{VaR}_{95\%}]$$

Cette métrique, aussi appelée Expected Shortfall, est plus robuste que la VaR car elle capture la queue de distribution au-delà du quantile [@RockafellarUryasev2000].

### Beta vs benchmark

Le beta du portefeuille vis-à-vis d'un benchmark est calculé classiquement comme :

$$\beta = \frac{\text{Cov}(r_p, r_b)}{\text{Var}(r_b)}$$

où $r_p$ et $r_b$ sont respectivement les rendements journaliers du portefeuille et du benchmark, alignés temporellement. Le benchmark par défaut est un 60/40 simplifié constitué de 60 % CSPX.L (S&P 500) et 40 % IB01.L (Treasury 0-1 an), reconstruit synthétiquement à partir des prix journaliers.

\newpage

# Résultats empiriques

## Données utilisées

Les résultats présentés couvrent la période du 8 mai 2023 au 8 mai 2026, soit trois années glissantes. Les prix des 49 ETFs sont extraits de Yahoo Finance via la bibliothèque `yfinance`. Les six séries macroéconomiques sont extraites de la base FRED via la bibliothèque `fredapi`, avec authentification par clé API personnelle.

Tous les rendements sont calculés sur les prix de clôture quotidiens, sans prise en compte des dividendes (les ETFs UCITS étant majoritairement à accumulation, ce biais est limité). Les jours de marché fériés sont exclus (`freq='B'` dans pandas).

## État du système au 8 mai 2026

Le tableau 6 présente les lectures des six indicateurs macroéconomiques au 8 mai 2026. Le tableau 7 résume l'agrégation par dimension et le régime classifié.

**Tableau 6 — Lectures macroéconomiques au 8 mai 2026**

| Indicateur | Valeur | Z-score | Direction | Confidence |
|---|---:|---:|:---:|---:|
| Yield curve 10y3m | +0.74 % | +0.71 | UP | 64 % |
| Industrial Production YoY | +0.74 % | -0.14 | NEUTRAL | 40 % |
| Initial Jobless Claims (MA4) | 207 500 | -0.56 | UP | 61 % |
| 5y5y Forward Inflation | +2.27 % | +0.06 | NEUTRAL | 40 % |
| Core CPI YoY | +2.67 % | -1.30 | DOWN | 76 % |
| WTI Oil 6m Momentum | +68.45 % | +2.70 | UP | 95 % |

**Tableau 7 — Agrégation et classification**

| Dimension | Direction | Score agrégé | Confidence agrégée |
|---|:---:|---:|---:|
| Croissance | UP | +0.76 | 42 % |
| Inflation | NEUTRAL | +0.09 | 6 % |

Le régime classifié est **Incertain** avec une confidence de 6 % (minimum des deux dimensions).

L'examen des lectures inflation est instructif. Le Core CPI YoY se situe à 2.67 %, soit en valeur absolue une inflation modérée, mais le z-score à -1.30 reflète une décélération marquée par rapport à la moyenne des cinq dernières années (qui inclut la flambée 2022). Simultanément, le momentum WTI sur six mois s'établit à +68 % (z = +2.70), signe d'une réaccélération forte des prix du pétrole qui se traduira mécaniquement dans le headline CPI à un horizon de 3-6 mois. Le breakeven 5y5y, au milieu, ne tranche pas. Cette divergence forte entre inflation observée (en désinflation) et inflation forward-looking (en réaccélération) explique la confidence très basse de la dimension.

Le système refuse à juste titre de classifier dans cette configuration. L'allocation produite est par conséquent identique à la référence neutre, avec un écart maximal de 0.0 % par classe d'actifs.

## Performance simulée sur 3 ans

Bien que l'allocation actuelle soit neutre, la performance simulée du portefeuille construit par le système sur la fenêtre mai 2023 - mai 2026 fournit une indication préliminaire de la qualité du benchmark interne et de la sélection de fonds. Le tableau 8 compare le portefeuille au benchmark 60/40 standard sur les sept métriques de risque.

**Tableau 8 — Performance comparée sur 3 ans (mai 2023 - mai 2026)**

| Métrique | Portefeuille | Benchmark 60/40 | Écart |
|---|---:|---:|---:|
| Rendement annualisé | +25.67 % | +21.06 % | +4.61 pt |
| Volatilité annualisée | 7.18 % | 7.32 % | -0.14 pt |
| Ratio de Sharpe | +3.23 | +2.53 | +0.70 |
| Maximum drawdown | -5.48 % | -4.74 % | -0.74 pt |
| VaR 95 % (journalière) | -0.63 % | -0.66 % | +0.03 pt |
| CVaR 95 % (journalière) | -0.87 % | -0.86 % | -0.01 pt |
| Beta vs 60/40 | +0.86 | +1.00 | -0.14 |

Le portefeuille surperforme le benchmark sur cinq des sept métriques (rendement, volatilité, Sharpe, VaR, beta) et sous-performe marginalement sur deux (drawdown, CVaR).

## Analyse de la surperformance

La surperformance annualisée de 4.6 points est significative en valeur absolue, mais sa décomposition appelle plusieurs nuances importantes.

**Premièrement**, sur la fenêtre considérée, le régime détecté est resté majoritairement Incertain, ce qui implique que l'allocation produite a été proche de la référence neutre la plupart du temps. La surperformance ne peut donc être attribuée majoritairement au timing tactique macro.

**Deuxièmement**, la composition de la référence neutre elle-même diffère du benchmark 60/40 simplifié. Le neutre comprend 50 % d'actions (40 % DM + 10 % EM) contre 60 % de S&P 500 dans le benchmark, mais il inclut 5 % d'or et 5 % de foncier coté qui ont contribué positivement sur la période, ainsi qu'une diversification obligataire (souverain + crédit IG + crédit HY) là où le benchmark se limite au Treasury 0-1 an. Une part substantielle de la surperformance s'explique donc par la composition multi-actifs structurelle, indépendamment de toute décision tactique.

**Troisièmement**, le scoring composite intra-poche favorise systématiquement les ETFs au plus haut Sharpe sur 3 ans, ce qui introduit un biais ex-post : les fonds qui ont le mieux performé sur la fenêtre passée sont mécaniquement surreprésentés. Ce biais sera atténué dans une démarche de backtest pluriannuel où le scoring sera calculé point-in-time.

**Quatrièmement**, la fenêtre de 3 ans (mai 2023 - mai 2026) couvre une période de marché globalement favorable aux actifs risqués (sortie du choc inflationniste 2022, désinflation graduelle, anticipation de baisse des taux). Cette configuration favorise structurellement les portefeuilles diversifiés multi-actifs comme le nôtre.

Une décomposition rigoureuse de l'attribution (allocation strategic vs allocation tactique vs sélection de fonds) requerrait un backtest formel sur 15-20 ans avec rebalancement mensuel point-in-time. Cette analyse constitue un axe d'amélioration prioritaire (cf. section 7).

## Composition du portefeuille au 8 mai 2026

Le tableau 9 présente la composition concrète du portefeuille initialisé avec un capital de 100 000 €. La confidence de régime étant de 6 %, l'allocation est quasi-identique à la référence neutre.

**Tableau 9 — Portefeuille initial au 8 mai 2026 (capital : 100 000 €)**

| Ticker | Nom | Classe d'actifs | Poids | Quantité | Prix |
|---|---|---|---:|---:|---:|
| CSPX.L | iShares Core S&P 500 UCITS | Actions DM | 20.00 % | 25.22 | 793.01 € |
| IWVL.L | iShares Edge MSCI World Value | Actions DM | 20.00 % | 272.46 | 73.40 € |
| IB01.L | iShares Treasury Bond 0-1yr | Souverain | 10.00 % | 83.11 | 120.32 € |
| IBGS.AS | iShares Euro Govt Bond 1-3yr | Souverain | 10.00 % | 71.08 | 140.68 € |
| EIMI.L | iShares Core MSCI EM IMI | Actions EM | 5.00 % | 90.81 | 55.06 € |
| VFEM.L | Vanguard FTSE Emerging Markets | Actions EM | 5.00 % | 81.04 | 61.70 € |
| VDCA.L | Vanguard USD Corporate Bond | Crédit IG | 5.00 % | 81.04 | 61.70 € |
| VDCP.L | Vanguard EUR Corporate Bond | Crédit IG | 5.00 % | 105.19 | 47.53 € |
| IGLN.L | iShares Physical Gold ETC | Or | 5.00 % | 54.31 | 92.07 € |
| IHYU.L | iShares USD HY Corporate Bond | Crédit HY | 2.50 % | 26.17 | 95.52 € |
| IHYG.L | iShares Euro HY Corporate Bond | Crédit HY | 2.50 % | 27.39 | 91.27 € |
| IUSP.L | iShares US Property Yield | Foncier | 2.50 % | 1.03 | 2 425.75 € |
| IWDP.L | iShares Developed Markets Property | Foncier | 2.50 % | 1.30 | 1 930.50 € |
| XEON.DE | Xtrackers EUR Overnight Rate Swap | Cash | 2.50 % | 16.77 | 149.06 € |
| ERNS.L | iShares USD Ultrashort Bond | Cash | 2.50 % | 24.73 | 101.10 € |
| | **Total** | | **100.00 %** | | |

L'allocation est diversifiée à travers 15 lignes individuelles couvrant 8 classes d'actifs. La géographie est mixte (US, Europe, EM), la duration obligataire est principalement courte, et l'exposition aux actifs réels (or + foncier) totalise 10 % du portefeuille.

\newpage

# Discussion

## Forces du framework

**Transparence méthodologique**. Chaque décision allocative peut être tracée jusqu'aux données macroéconomiques sous-jacentes. Cela contraste avec les approches discrétionnaires opaques et avec certaines approches quantitatives black-box (réseaux neuronaux profonds, par exemple).

**Robustesse aux signaux faibles**. Le mécanisme de smoothing par confidence garantit qu'aucune décision tactique extrême ne peut être prise sur la base de signaux statistiquement fragiles. Cette propriété est particulièrement précieuse en période de transition de régime, où les indicateurs sont typiquement contradictoires.

**Modularité architecturale**. La séparation stricte des sept modules permet de substituer indépendamment la logique de détection de régime, d'allocation, de sélection ou de mesure du risque. Cela facilite les évolutions futures (par exemple, le passage à un modèle de Markov caché pour la détection de régime) sans remettre en cause l'ensemble du framework.

**Ingénierie logicielle disciplinée**. Le projet respecte les standards de qualité d'un projet logiciel professionnel : 161 tests unitaires couvrant 90 % du code, type checking strict (mypy), formatage automatique (ruff), intégration continue (GitHub Actions). Ces pratiques réduisent significativement le risque de bugs silencieux et facilitent la maintenance long terme.

## Limites assumées

**Absence de backtest pluriannuel**. La validation empirique présentée en section 5 couvre 3 années glissantes, ce qui est insuffisant pour valider statistiquement la valeur ajoutée du timing macro. Un backtest formel sur 15-20 ans avec rebalancement mensuel point-in-time est en cours de développement et constitue le chantier prioritaire de la V2.

**Tilts non calibrés empiriquement**. Les valeurs des tilts par régime sont calibrées qualitativement à partir de la littérature et de l'intuition macroéconomique, sans optimisation empirique sur historique. Une grid search ou une optimisation bayésienne sur les paramètres pourrait améliorer la performance, mais introduirait également un risque significatif de surapprentissage.

**Indicateurs macro US uniquement**. Le framework s'appuie exclusivement sur des indicateurs américains. Cette restriction se justifie par la centralité de la Fed dans les flux financiers mondiaux et par la richesse des données FRED, mais elle introduit un biais : si le régime macro européen ou émergent diverge fortement du régime US, le framework ne le détectera pas. L'ajout d'indicateurs ECB et asiatiques constitue un axe d'amélioration de second ordre.

**Absence de coûts de transaction**. La simulation actuelle ignore les frais de transaction et le slippage, ce qui surestime la performance nette pour des rebalancements mensuels avec turnover non négligeable. Une modélisation simple (frais de courtage forfaitaires + spread bid-ask) sera intégrée dans la V2.

**Pas de gestion fiscale**. Le framework ne prend pas en compte le traitement fiscal différencié selon l'enveloppe (PEA, assurance-vie, compte-titres ordinaire). Ceci est acceptable pour un cadre de recherche méthodologique, mais constituerait une limite significative pour un déploiement opérationnel sur un mandat privé.

**Univers limité à 49 ETFs UCITS**. Le choix d'un univers restreint privilégie la cohérence et la liquidité au détriment de la couverture. Certaines classes d'actifs sont sous-représentées (un seul fonds en or physique, deux fonds en commodities broad). Un élargissement progressif à 100-150 lignes permettrait d'enrichir le scoring intra-poche.

**Pas de signaux alternatifs**. Le framework ignore les données alternatives potentiellement informatives : positionnement institutionnel CFTC, flux ETF, sentiment de marché (VIX, indicateurs sentiment retail), positionnement options (put/call ratio). Ces signaux pourraient compléter les indicateurs macro fondamentaux.

## Robustesse opérationnelle

Une attention particulière a été portée à la résilience du système face aux pannes des API externes. La base FRED retourne occasionnellement des erreurs HTTP 500 sur certaines séries, en particulier les séries d'énergie. Sans mécanisme de retry, ces pannes peuvent conduire à des classifications de régime incohérentes d'un mois à l'autre uniquement à cause de défaillances tech transitoires.

Le `FREDProvider` du framework intègre un mécanisme de retry avec backoff exponentiel : trois tentatives au maximum, avec attentes de 1, 2 et 4 secondes entre chaque retry. Le système distingue les erreurs transitoires (codes HTTP 5xx, erreurs réseau) des erreurs fatales (codes 4xx, mauvais identifiant de série), et ne retry que les premières.

Cette robustesse a été validée empiriquement lors d'incidents observés en avril-mai 2026 sur les séries `DCOILBRENTEU` (Brent crude oil) et `T10Y3M` (yield curve). Dans le premier cas, la panne s'est révélée persistante et le framework a basculé en utilisant `DCOILWTICO` (WTI), avec documentation explicite du changement. Dans le second cas, une simple répétition après backoff a suffi à récupérer la donnée.

## Comparaison avec les approches alternatives

**Vs allocation statique 60/40**. Le framework offre une allocation plus diversifiée (8 classes d'actifs vs 2) et adaptable au régime macro. Le coût est une complexité accrue, qui ne se justifie que si la confidence du régime est suffisamment élevée pour produire des écarts tactiques significatifs.

**Vs Markowitz mean-variance**. L'approche Markowitz est théoriquement optimale sous hypothèse de normalité des rendements et de connaissance des moments futurs. En pratique, elle est très sensible aux estimations d'inputs (matrice de covariance, vecteur de rendements attendus), ce qui produit des allocations instables (« corner solutions »). Notre framework règle-based est moins théoriquement élégant mais beaucoup plus stable empiriquement.

**Vs Black-Litterman**. L'approche Black-Litterman combine équilibre de marché (CAPM) et views actives via inférence bayésienne. Elle reste théoriquement supérieure pour intégrer des views subjectives, mais sa mise en œuvre opérationnelle est complexe (paramétrage des incertitudes des views, choix du paramètre $\tau$). Notre framework pourrait évoluer vers une formulation Black-Litterman dans une V3, en utilisant les régimes comme prior.

**Vs Hidden Markov Models**. Une détection de régime par chaîne de Markov cachée [@Hamilton1989] serait théoriquement plus rigoureuse que notre approche par seuillage z-score. Elle permet de calibrer empiriquement les transitions entre régimes et d'intégrer la dépendance temporelle. Toutefois, les HMM nécessitent une quantité importante de données pour stabiliser leurs estimations, et leur interprétabilité est moindre que celle de notre approche règle-based. Cette piste est conservée pour une éventuelle V3.

**Vs approches machine learning**. Des modèles ML sophistiqués (random forests, gradient boosting, réseaux neuronaux) pourraient en principe découvrir des relations non-linéaires entre indicateurs macro et rendements futurs des classes d'actifs. En pratique, le risque de surapprentissage est très élevé sur des séries macro à fréquence basse, et l'interprétabilité (cruciale pour la défense d'un framework auprès d'un comité d'investissement) est très dégradée. Notre choix de rester sur une approche règle-based interprétable est délibéré.

\newpage

# Conclusion et travaux futurs

Nous avons présenté *Bordeaux Multi-Asset Lab*, un framework systématique d'allocation tactique multi-actifs guidé par le régime macroéconomique. Le système combine quatre briques distinctes : une classification parmi cinq régimes basée sur six indicateurs FRED, une table de tilts modérés autour d'une référence neutre 60/40 enrichie, un mécanisme de smoothing par confidence, et une sélection de fonds par scoring composite au sein d'un univers UCITS de 49 ETFs.

La validation empirique préliminaire sur la période mai 2023 - mai 2026 indique une surperformance annualisée de 4.6 points par rapport à un benchmark 60/40 standard, avec une volatilité comparable et un ratio de Sharpe supérieur de 0.7 unité. Toutefois, nous insistons sur le fait qu'à la date de mai 2026, le régime détecté est *Incertain* avec une confidence de 6 %, ce qui place l'allocation à 95 % alignée sur la référence neutre. La surperformance observée est donc principalement attribuable à la composition multi-actifs structurelle de la référence et au scoring intra-poche, et non au timing tactique macroéconomique.

## Roadmap d'évolution

Trois chantiers prioritaires sont identifiés pour la V2.

**Backtest pluriannuel**. Reconstruction de l'historique des régimes mensuels depuis 2000 (en respectant scrupuleusement le caractère point-in-time des indicateurs), avec rebalancement mensuel et calcul de l'attribution de performance entre allocation strategic, allocation tactique, et sélection de fonds. Cette analyse permettra de quantifier la valeur ajoutée propre du timing macroéconomique et de calibrer empiriquement les tilts par régime.

**Modélisation des coûts de transaction**. Intégration d'un modèle simple de frais (frais de courtage forfaitaires + spread bid-ask + impact prix proportionnel au turnover). Cette extension permettra d'évaluer la performance nette réaliste et de tester la sensibilité du framework à différents scenarii de coûts.

**Élargissement géographique des indicateurs macro**. Ajout d'au moins un indicateur ECB (taux directeur ECB, HICP eurozone) et un indicateur Chine (PMI Caixin manufacturier ou non-manufacturier). Cet élargissement permettra de détecter les divergences régionales et d'enrichir le diagnostic du régime mondial.

## Discipline de publication mensuelle

À partir du 5 juillet 2026, une lettre d'investissement mensuelle est publiée le 5 de chaque mois. Cette lettre présente le régime détecté, l'allocation cible, le portefeuille concret avec ses transactions de rebalancement, et la performance écoulée. La régularité de cette publication constitue le mécanisme principal de validation publique du framework et de construction d'un track record vérifiable.

Le code source complet, la configuration de l'univers, les résultats détaillés, et les lettres mensuelles publiées sont accessibles à l'adresse suivante :

`https://github.com/TTB10/bordeaux-multi-asset-lab`

\newpage

# Références {-}

::: {#refs}
:::

[@AngBekaert2002] Ang, A., & Bekaert, G. (2002). International Asset Allocation with Regime Shifts. *Review of Financial Studies*, 15(4), 1137-1187.

[@AsnessFrazziniPedersen2012] Asness, C. S., Frazzini, A., & Pedersen, L. H. (2012). Leverage Aversion and Risk Parity. *Financial Analysts Journal*, 68(1), 47-59.

[@BlackLitterman1992] Black, F., & Litterman, R. (1992). Global Portfolio Optimization. *Financial Analysts Journal*, 48(5), 28-43.

[@Brinson1986] Brinson, G. P., Hood, L. R., & Beebower, G. L. (1986). Determinants of Portfolio Performance. *Financial Analysts Journal*, 42(4), 39-44.

[@Carhart1997] Carhart, M. M. (1997). On Persistence in Mutual Fund Performance. *Journal of Finance*, 52(1), 57-82.

[@Dalio2017] Dalio, R. (2017). *Principles: Life and Work*. Simon & Schuster.

[@EstrellaMishkin1998] Estrella, A., & Mishkin, F. S. (1998). Predicting U.S. Recessions: Financial Variables as Leading Indicators. *Review of Economics and Statistics*, 80(1), 45-61.

[@Faber2007] Faber, M. T. (2007). A Quantitative Approach to Tactical Asset Allocation. *Journal of Wealth Management*, 9(4), 69-79.

[@Hamilton1989] Hamilton, J. D. (1989). A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle. *Econometrica*, 57(2), 357-384.

[@Ibbotson2000] Ibbotson, R. G., & Kaplan, P. D. (2000). Does Asset Allocation Policy Explain 40, 90, or 100 Percent of Performance? *Financial Analysts Journal*, 56(1), 26-33.

[@Markowitz1952] Markowitz, H. (1952). Portfolio Selection. *Journal of Finance*, 7(1), 77-91.

[@Martin2017] Martin, R. C. (2017). *Clean Architecture: A Craftsman's Guide to Software Structure and Design*. Prentice Hall.

[@RockafellarUryasev2000] Rockafellar, R. T., & Uryasev, S. (2000). Optimization of Conditional Value-at-Risk. *Journal of Risk*, 2, 21-42.

[@Sharpe1966] Sharpe, W. F. (1966). Mutual Fund Performance. *Journal of Business*, 39(1), 119-138.

[@SortinoPrice1994] Sortino, F. A., & Price, L. N. (1994). Performance Measurement in a Downside Risk Framework. *Journal of Investing*, 3(3), 59-64.

[@Young1991] Young, T. W. (1991). Calmar Ratio: A Smoother Tool. *Futures*, 20(1), 40.

\newpage

# Annexe A — Composition de l'univers {-}

L'univers d'investissement comprend 49 ETFs UCITS européens. Le tableau A.1 liste les principales lignes par classe d'actifs. La liste exhaustive est disponible dans le fichier `src/bml/config/universe.yaml` du dépôt GitHub.

**Tableau A.1 — Principales lignes de l'univers**

| Classe d'actifs | Ticker | Nom |
|---|---|---|
| Actions DM | CSPX.L | iShares Core S&P 500 UCITS |
| Actions DM | IWDA.AS | iShares Core MSCI World UCITS |
| Actions DM | IWVL.L | iShares Edge MSCI World Value Factor |
| Actions DM | IUIT.L | iShares S&P 500 IT Sector UCITS |
| Actions EM | EIMI.L | iShares Core MSCI EM IMI UCITS |
| Actions EM | VFEM.L | Vanguard FTSE Emerging Markets UCITS |
| Souverain | IB01.L | iShares Treasury Bond 0-1yr UCITS |
| Souverain | IBGS.AS | iShares Euro Govt Bond 1-3yr UCITS |
| Souverain | IDTL.L | iShares Treasury Bond 7-10yr UCITS |
| Crédit IG | VDCA.L | Vanguard USD Corporate Bond UCITS |
| Crédit IG | VDCP.L | Vanguard EUR Corporate Bond UCITS |
| Crédit HY | IHYU.L | iShares USD HY Corporate Bond UCITS |
| Crédit HY | IHYG.L | iShares Euro HY Corporate Bond UCITS |
| Or | IGLN.L | iShares Physical Gold ETC |
| Argent | PHAG.L | WisdomTree Physical Silver |
| Commodities | ICOM.L | iShares Diversified Commodity Swap UCITS |
| Foncier | IUSP.L | iShares US Property Yield UCITS |
| Foncier | IWDP.L | iShares Developed Markets Property Yield |
| Cash | XEON.DE | Xtrackers EUR Overnight Rate Swap UCITS |
| Cash | ERNS.L | iShares USD Ultrashort Bond UCITS |

\newpage

# Annexe B — Glossaire technique {-}

**Beta** : sensibilité d'un actif aux mouvements d'un benchmark de référence, calculée comme la covariance des rendements normalisée par la variance du benchmark.

**CVaR (Conditional Value at Risk)** : moyenne des rendements en deçà du quantile de la VaR. Aussi appelé Expected Shortfall. Plus robuste que la VaR pour mesurer le tail risk.

**Drawdown** : chute peak-to-trough d'un actif sur une période. Le maximum drawdown est la pire chute observée.

**ETF (Exchange-Traded Fund)** : fonds coté en bourse, acheté et vendu comme une action.

**FRED (Federal Reserve Economic Data)** : base de données publique de séries macroéconomiques maintenue par la Réserve fédérale de Saint-Louis.

**Régime macroéconomique** : état caractérisé par une combinaison de conditions économiques (croissance, inflation, taux, etc.) qui tend à favoriser certaines classes d'actifs.

**Sharpe ratio** : rendement excédentaire (rendement total moins taux sans risque) par unité de volatilité.

**Smoothing par confidence** : mécanisme d'interpolation entre une allocation de référence et une allocation cible, pondérée par la confiance dans le signal.

**TER (Total Expense Ratio)** : frais courants annuels d'un fonds, exprimés en pourcentage des actifs sous gestion.

**Tilt** : écart d'une allocation tactique vis-à-vis d'une allocation de référence, généralement exprimé en points de pourcentage par classe d'actifs.

**UCITS (Undertakings for Collective Investment in Transferable Securities)** : cadre réglementaire européen harmonisé pour les fonds collectifs ouverts au grand public.

**VaR (Value at Risk)** : perte maximale attendue à un horizon donné et un niveau de confiance donné. La VaR 95 % à un jour est le 5e percentile de la distribution des rendements journaliers.

**Z-score** : statistique standardisée définie comme (valeur - moyenne) / écart-type. Permet de comparer des grandeurs aux échelles différentes.

---

*© TTB10, 2026. Ce document est mis à disposition sous licence Creative Commons BY-SA 4.0. Le code source associé est sous licence MIT.*
