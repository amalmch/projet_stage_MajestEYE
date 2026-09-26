# 📊 Guide d'Installation et Configuration — Metabase pour SONEDE

Ce guide explique comment lancer **Metabase** localement via Docker, le connecter directement à **MongoDB** (sans ETL), et configurer les **deux tableaux de bord** (Administration Générale & Service Technique).

---

## 🚀 Étape 1 : Lancement de Metabase via Docker

À la racine du projet (`c:\PROJET_STAGE_AMAL`), lancez :

```bash
docker compose -f docker-compose.metabase.yml up -d
```

Metabase démarrera sur **`http://localhost:8085`**.  
*(Le premier démarrage prend environ 1 à 2 minutes).*

---

## 🔌 Étape 2 : Connexion de MongoDB dans Metabase

1. Ouvrez **`http://localhost:8085`** et suivez l'assistant de démarrage (créez votre compte administrateur).
2. Quand Metabase demande d'ajouter des données :
   - **Type de base de données** : `MongoDB`
   - **Nom de la base** : `SONEDE Smart Platform`
   - **Hôte (Host)** : `host.docker.internal` *(ou `mongodb` si dans le même réseau docker)*
   - **Port** : `27017`
   - **Nom de la base de données (Database name)** : `sonede_smart_platform`
   - **Identifiants** : Laissez vide si sans mot de passe, ou mettez `root` / `secret` selon votre config.
3. Cliquez sur **Sauvegarder**. Metabase va analyser la collection `complaints`.

---

## 📈 Étape 3 : Création des Graphiques du Tableau de Bord (Admin Générale)

Dans Metabase, cliquez sur **"+ Nouveau" → "Question" → "Requête Native (Native query)"**.  
Choisissez la base MongoDB `SONEDE Smart Platform`.

### 1. 📊 Rectangles de Statistiques (KPI Counters)

Dans l'éditeur JSON de Metabase, coller les requêtes du fichier [`metabase/queries/kpi_counters.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/kpi_counters.json) :
- **Total Réclamations** → Type de visualisation : *Number* (Nombre)
- **% Critiques** → Type de visualisation : *Number* (Suffixe: `%`)
- **Zones Touchées** → Type de visualisation : *Number*
- **Temps Moyen Résolution** → Type de visualisation : *Number* (Suffixe: `jours`)
- **Taux de Résolution** → Type de visualisation : *Number* (Suffixe: `%`)

### 2. 📊 Bar Chart (Réclamations par Type selon chaque Région)

Coller le JSON du fichier [`metabase/queries/bar_chart.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/bar_chart.json) :
- Type de visualisation : **Bar Chart (Histogramme)**
- Axe X : `gouvernorat`
- Axe Y : `nb_reclamations`
- Regrouper par : `type_reclamation`
- Empilement : **Stacked (Empilé)**

### 3. 🗺️ Carte Géographique de la Tunisie (Leaflet)

Coller le JSON de [`metabase/queries/map_data.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/map_data.json) :
- Metabase propose une carte intégrée (Latitude/Longitude).
- Pour le rendu personnalisé avec cercles de criticité rouges/oranges/verts, ouvrez [`metabase/custom_viz/tunisia_map.html`](file:///c:/PROJET_STAGE_AMAL/metabase/custom_viz/tunisia_map.html) dans un widget HTML/Iframe.

### 4. 🕸️ Radar Chart (Top Problèmes par Mois)

Utiliser [`metabase/queries/radar_data.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/radar_data.json).  
Pour l'affichage sous forme de toile d'araignée, intégrer [`metabase/custom_viz/radar_chart.html`](file:///c:/PROJET_STAGE_AMAL/metabase/custom_viz/radar_chart.html).

### 5. 🌳 Tree Chart (Hiérarchie Région → Problème → Urgence)

Utiliser [`metabase/queries/treemap_data.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/treemap_data.json).  
Intégrer [`metabase/custom_viz/treemap_chart.html`](file:///c:/PROJET_STAGE_AMAL/metabase/custom_viz/treemap_chart.html).

### 6. 📋 Table Détaillée des Réclamations

Coller le JSON de [`metabase/queries/detail_table.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/detail_table.json).  
- Type de visualisation : **Table**

### 7. 🍂 Charte d'Analyse Saisonnière (Types par Saison)

Coller le JSON de [`metabase/queries/seasonal_analysis.json`](file:///c:/PROJET_STAGE_AMAL/metabase/queries/seasonal_analysis.json).  
- Type de visualisation : **Stacked Bar Chart (Empilé)**
- Axe X : `saison`
- Axe Y : `nb_reclamations`
- Regrouper par : `type_reclamation`

---

## 🎯 Étape 4 : Assemblage du Dashboard Administration

1. Cliquez sur **"+ Nouveau" → "Tableau de bord"**.
2. Nommez-le : `SONEDE - Administration Générale`.
3. Ajoutez toutes les questions créées ci-dessus.
4. Ajoutez les **Filtres de tableau de bord** en haut :
   - **Année**
   - **Saison** (Hiver, Printemps, Été, Automne)
   - **Catégorie / Type de Réclamation**
   - **Gouvernorat / Région**

---

## ☁️ Étape 5 : Déploiement en Production (Railway / Render / Cloud)

Pour héberger ce Metabase en ligne (alternative Vercel) :
1. Créez un compte gratuit sur [Railway.app](https://railway.app) ou [Render.com](https://render.com).
2. Déployez le conteneur Docker `metabase/metabase:latest`.
3. Connectez l'URI MongoDB de votre base de données de production.
