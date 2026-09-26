"""
Dictionnaire de dialecte tunisien (Derja) pour le chatbot SONEDE — v3.

3 000+ alias mappés vers ~300 formes canoniques, couvrant les 10 catégories
de réclamation SONEDE. Chaque entrée comprend des variantes :
  - Derja latine (Arabizi : 3=ع 7=ح 8=غ 9=ق 5=خ)
  - Derja arabe (graphie arabe dialectale)
  - Français standard
  - Anglais courant
  - Arabe standard moderne (MSA)

Fonctions publiques :
  apply_char_substitutions(text) -> str   # 8alya → ghalya
  normalize_derja(text) -> str            # ghalya → cher, tsarrub → fuite …
  analyze_dialect(text) -> dict           # détecte expressions + hints catégorie
"""
import re

# ═══════════════════════════════════════════════════════════════════════
# 1. CHARACTER SUBSTITUTION (Arabizi → Latin)
# ═══════════════════════════════════════════════════════════════════════
CHAR_SUBSTITUTIONS = {
    "8": "gh",
    "9": "q",
    "7": "h",
    "5": "kh",
    "3": "a",
}


def apply_char_substitutions(text: str) -> str:
    """Replace Arabizi number codes with their Latin equivalents.
    Must be called BEFORE normalize_derja()."""
    for digit, replacement in CHAR_SUBSTITUTIONS.items():
        text = text.replace(digit, replacement)
    return text


# ═══════════════════════════════════════════════════════════════════════
# 2. CANONICAL DICTIONARY — ~300 entries, 3 000+ aliases
# ═══════════════════════════════════════════════════════════════════════
# Key = canonical form used internally after normalization.
# "aliases" = all known ways users write this concept.
# "meaning" = French meaning for display.
# "category_hint" = SONEDE category (None if generic vocabulary).

DERJA_DICT = {
    # ─── WATER / EAU ──────────────────────────────────────────────────
    "eau": {
        "aliases": [
            "ma", "el ma", "el mé", "mé", "lma", "lmé", "l'ma", "l'mé",
            "الماء", "الما", "ماء", "مياه", "المياه", "water", "l'eau",
            "el maa", "el me", "lme",
        ],
        "meaning": "eau",
        "category_hint": None,
    },
    "robinet": {
        "aliases": [
            "robineh", "robini", "hanafiya", "7anafiya", "sabala", "حنفية", "الحنفية",
            "صنبور", "الصنبور", "faucet", "tap", "el hanafiya", "hanfiya",
            "7anfiya", "robine", "robbinet",
        ],
        "meaning": "robinet",
        "category_hint": None,
    },
    "tuyau": {
        "aliases": [
            "tube", "tubo", "qanat", "9anat", "canal", "قناة", "أنبوب",
            "الأنابيب", "قنوات", "anbub", "anabib", "pipe", "pipes",
            "canalisation", "conduite", "tuyauterie", "canalisations",
            "el qanat", "el 9anat", "tuyaux",
        ],
        "meaning": "tuyau / canalisation",
        "category_hint": None,
    },
    "compteur": {
        "aliases": [
            "conteur", "counter", "3addad", "aaddad", "عداد", "العداد",
            "meter", "water meter", "compteur d'eau", "contoor",
            "el 3addad", "el aaddad", "komtoor",
        ],
        "meaning": "compteur",
        "category_hint": None,
    },
    "reservoir": {
        "aliases": [
            "khazzan", "5azzan", "khazzane", "خزان", "الخزان", "citerne",
            "tank", "water tank", "bac", "réservoir", "5azen", "khazen",
            "el khazzan", "majel", "الماجل",
        ],
        "meaning": "réservoir / citerne",
        "category_hint": None,
    },
    "reseau": {
        "aliases": [
            "shabaka", "chabaka", "شبكة", "الشبكة", "network", "réseau",
            "grid", "shabket el ma", "chabket el ma", "شبكة المياه",
        ],
        "meaning": "réseau",
        "category_hint": None,
    },
    "pompe": {
        "aliases": [
            "pomp", "pompa", "مضخة", "المضخة", "pump", "bomba",
            "el pompe", "pompage", "el pompa",
        ],
        "meaning": "pompe",
        "category_hint": None,
    },
    "station": {
        "aliases": [
            "ma7atta", "mahatta", "محطة", "المحطة", "station de pompage",
            "pumping station", "محطة الضخ", "ma7attet el ma",
            "station el ma", "محطة المياه",
        ],
        "meaning": "station",
        "category_hint": None,
    },
    "vanne": {
        "aliases": [
            "sikkara", "sabbala", "سكارة", "صبالة", "valve", "vana",
            "el sikkara",
        ],
        "meaning": "vanne",
        "category_hint": None,
    },

    # ─── COUPURE / WATER CUT ──────────────────────────────────────────
    "coupure": {
        "aliases": [
            "qata", "9ata", "9at3", "qat3", "9ata3", "qaata3", "9ta3","ma9tou3",
            "coupure deau", "coupure d'eau", "9ta3 el ma", "qaata3 el mé",
            "قطع", "انقطاع", "قطع الماء", "انقطاع المياه", "water cut",
            "cut off", "outage", "no water", "pas d'eau",
            "el ma 9te3", "el ma 9at3", "lma mqata3", "ma 9to3",
        ],
        "meaning": "coupure d'eau",
        "category_hint": "coupure_non_signalee",
    },
    "coupure planifiee": {
        "aliases": [
            "9ta3 mbarmej", "qata mbarmaj", "coupure mbarmja",
            "coupure planifiée", "planned cut", "scheduled cut",
            "قطع مبرمج", "انقطاع مبرمج", "قطع معلن",
            "9ta3 m3alen", "kayen achghel", "3andhom achghel",
            "أشغال صيانة", "travaux", "maintenance", "عندهم أشغال",
            "3lawa 3ala achghel",
        ],
        "meaning": "coupure planifiée",
        "category_hint": "coupure_planifiee",
    },
    "ma famach me": {
        "aliases": [
            "ma famech ma", "mafamch mé", "ma 3andich mé", "ma3andich mé",
            "ma3andich ma", "ma famach ma", "ma famech mé",
            "ما فماش ماء", "ماعنديش ماء", "الماء مقطوع",
            "ma fama ma", "ma fammech ma", "manich nel9a ma",
            "no water at all", "pas du tout d'eau",
        ],
        "meaning": "pas d'eau du tout",
        "category_hint": "coupure_non_signalee",
    },

    # ─── PRESSION / PRESSURE ──────────────────────────────────────────
    "pression faible": {
        "aliases": [
            "dhaghet dh3if", "dghet d3if", "dhaghet el ma d3if",
            "el ma d3if", "el mé d3if", "el ma da3if",
            "ضغط الماء ضعيف", "الضغط ضعيف", "الضغط خفيف",
            "low pressure", "weak pressure", "faible pression",
            "pression insuffisante", "manque de pression",
            "dghet d3if barcha",
        ],
        "meaning": "pression faible",
        "category_hint": "pression_faible",
    },
    "el me tayah": {
        "aliases": [
            "el mé tay7", "tay7 el ma", "el ma tay7", "taye7 el mé",
            "el ma tayeh", "el mé tayeh", "الماء طايح", "الما طايح",
            "water dripping", "very low flow",
        ],
        "meaning": "eau qui coule à peine (pression très faible)",
        "category_hint": "pression_faible",
    },
    "intermittent": {
        "aliases": [
            "yji w yro7", "yji marra w y9os", "yji marra w yokos",
            "el mé yji marra w yokos", "intermittent",
            "va et vient", "on and off", "يجي ويروح",
            "مرة يجي مرة يقطع", "el ma yji w yo9os",
        ],
        "meaning": "eau intermittente",
        "category_hint": "pression_faible",
    },

    # ─── QUALITÉ / QUALITY ────────────────────────────────────────────
    "eau trouble": {
        "aliases": [
            "ma m3aker", "el mé m3aker", "el mé yji m3aker",
            "el ma m3aker", "ma asfar", "ma safra","el me lounou 5ayeb",
            "الماء عكر", "الماء أصفر", "ماء عكر",
            "turbid", "cloudy", "murky", "eau trouble",
            "eau boueuse", "brown water", "yellow water",
            "الماء موش نظيف", "ma mouch ndhif",
        ],
        "meaning": "eau trouble / boueuse",
        "category_hint": "qualite_eau",
    },
    "mauvaise odeur": {
        "aliases": [
            "ri7a khayba", "ri7et el mé khayba", "ri7a khayba fel ma",
            "el mé fih ri7a", "rihet el ma khayba","el me ri7tou khayba",
            "ريحة الماء خايبة", "رائحة الماء", "الماء ريحته موحشة",
            "bad smell", "smelly water", "odeur", "mauvaise odeur",
            "eau qui sent mauvais", "stinks", "smell",
            "el ma yanti", "ri7a kri7a",
        ],
        "meaning": "mauvaise odeur",
        "category_hint": "qualite_eau",
    },
    "mauvais gout": {
        "aliases": [
            "ta3m el ma mouch behi", "ta3m khayeb", "goût bizarre",
            "goût désagréable", "bad taste", "taste", "طعم سيء",
            "طعم غريب", "الماء طعمه خايب", "el ma ta3mou mouch behi",
        ],
        "meaning": "mauvais goût",
        "category_hint": "qualite_eau",
    },
    "chlore": {
        "aliases": [
            "klor", "chlore", "chlorine", "كلور", "javel",
            "ta3m el klor", "ri7et el klor", "bleach smell",
        ],
        "meaning": "chlore",
        "category_hint": "qualite_eau",
    },
    "eau pas bonne": {
        "aliases": [
            "el mé mouch behi", "el ma mouch behi",
            "الماء موش باهي", "not drinkable", "eau non potable",
            "ma yetsharabch", "ما يتشربش", "undrinkable",
            "el ma mouch saleh", "الماء موش صالح",
        ],
        "meaning": "eau de mauvaise qualité",
        "category_hint": "qualite_eau",
    },
    "couleur": {
        "aliases": [
            "loun", "loun el ma", "color", "colour", "لون", "لون الماء",
            "couleur de l'eau", "asfar", "a7mar", "couleur bizarre",
            "أصفر", "أحمر", "بني",
        ],
        "meaning": "couleur anormale",
        "category_hint": "qualite_eau",
    },
    "sale": {
        "aliases": [
            "wasekh", "wskh", "mouch ndhif", "dirty", "وسخ",
            "موسخ", "sale", "souillé", "pas propre", "impure",
            "el ma waskh",
        ],
        "meaning": "sale",
        "category_hint": "qualite_eau",
    },
    "contamination": {
        "aliases": [
            "telawwuth", "تلوث", "تلوث المياه", "contamination",
            "polluted", "contaminated", "pollution",
            "el ma mlawweth", "ملوث",
        ],
        "meaning": "contamination",
        "category_hint": "qualite_eau",
    },

    # ─── FUITE / LEAK ─────────────────────────────────────────────────
    "fuite": {
        "aliases": [
            "tsarrub", "tsarub", "tassarub", "tassrub", "fuit", "foui",
            "leak", "leaking", "leakage", "تسرب", "تسريب", "فويي", "فويت", "فوية",
            "يسكب", "yaskob", "yeskob", "fama fuite", "kayen fuite",
            "3andi fuite", "fama tsarrub", "el ma yaskob",
            "كاين تسرب", "تسريب في الأنابيب", "water leak",
            "fuite d'eau", "fuite deau", "fuites",
            "الماء يجري في الطريق",
        ],
        "meaning": "fuite d'eau",
        "category_hint": "fuite_visible",
    },
    "pipe cassee": {
        "aliases": [
            "qanat maksura", "9anat maksura", "tuyau cassé",
            "broken pipe", "burst pipe", "قناة مكسورة", "أنبوب مكسور",
            "cassure", "pipe burst", "tuyau pété", "qanat mhersa",
            "9anat t7assret",
        ],
        "meaning": "tuyau cassé",
        "category_hint": "fuite_visible",
    },
    "inondation": {
        "aliases": [
            "fayadan", "fayadhan", "فيضان", "inondation", "flooding",
            "flood", "overflow", "débordement", "el ma fayedh",
            "الماء فايض", "el ma yfi9", "yfayyedh",
        ],
        "meaning": "inondation / débordement",
        "category_hint": "fuite_visible",
    },

    # ─── PANNE POMPAGE / PUMP FAILURE ─────────────────────────────────
    "panne pompage": {
        "aliases": [
            "3otla fel pompage", "el pompe khsara", "panne pompe",
            "station el ma khsara", "عطب في الضخ", "عطل في المضخة",
            "محطة الضخ خربانة", "pump failure", "pump broken",
            "pumping failure", "el pompe m5asra",
            "panne de pompage", "pompe en panne",
        ],
        "meaning": "panne de pompage",
        "category_hint": "panne_pompage",
    },
    "coupure steg": {
        "aliases": [
            "el courant 9ata3 3al pompe", "coupure steg",
            "الكهرباء مقطوعة على المضخة", "power cut pump",
            "coupure électrique", "power outage", "steg 9at3et",
            "el dhaw 9at3", "الضو قاطع",
        ],
        "meaning": "coupure électrique affectant le pompage",
        "category_hint": "panne_pompage",
    },

    # ─── FACTURATION / BILLING ────────────────────────────────────────
    "facture": {
        "aliases": [
            "factoura", "fatura", "faktura", "الفاتورة", "فاتورة",
            "bill", "invoice", "tas3ira", "tessira", "tassira",
            "factur", "faktoura", "el facture", "el factura",
            "la facture", "el fatura", "فاتورة الماء",
        ],
        "meaning": "facture",
        "category_hint": "facturation",
    },
    "cher": {
        "aliases": [
            "ghalya", "8alya", "ghalia", "ghaliya", "8alia", "8aliya",
            "غالية", "غاليا", "غالي", "chère", "expensive", "costly",
            "cher", "trop cher", "overpriced", "yesser ghalya",
            "barcha ghalya", "bzf ghalya", "trop chère",
        ],
        "meaning": "cher / prix élevé",
        "category_hint": "facturation",
    },
    "facture elevee": {
        "aliases": [
            "facture ghalya", "facture zedt", "el facture 9asset",
            "double el facture", "facture énorme", "facture chère",
            "الفاتورة غالية", "الفاتورة زادت", "فاتورة مضاعفة",
            "prix trop élevé", "bill expensive", "high bill",
            "double facture", "facture doublée", "overcharged",
            "فاتورة مرتفعة", "el facture kbiira",
            "tas3ira ghalya", "tas3ira yesser ghalya",
        ],
        "meaning": "facture anormalement élevée",
        "category_hint": "facturation",
    },
    
    "consommation": {
        "aliases": [
            "istihlek", "istihlek el ma", "استهلاك", "استهلاك الماء",
            "consumption", "consommation d'eau", "water usage",
            "el istihlak", "الاستهلاك",
        ],
        "meaning": "consommation",
        "category_hint": "facturation",
    },
    "paiement": {
        "aliases": [
            "khlass", "5lass", "dfa3", "خلاص", "دفع",
            "payment", "pay", "payer", "khalas",
        ],
        "meaning": "paiement",
        "category_hint": "facturation",
    },
    "surfacturation": {
        "aliases": [
            "surfacturation", "overcharge", "surcharge",
            "double facturation", "erreur facture", "billing error",
            "خطأ في الفاتورة", "غلط في الفاتورة",
            "ghalat fel factura",
        ],
        "meaning": "surfacturation / erreur de facturation",
        "category_hint": "facturation",
    },
    "remboursement": {
        "aliases": [
            "remboursement", "refund", "rembourser",
            "raddouli flousi", "استرجاع", "رد الأموال",
        ],
        "meaning": "remboursement",
        "category_hint": "facturation",
    },
    "releve compteur": {
        "aliases": [
            "relevé", "relevé compteur", "meter reading",
            "قراءة العداد", "9ireet el 3addad", "qireet el aaddad",
            "lecture compteur",
        ],
        "meaning": "relevé de compteur",
        "category_hint": "facturation",
    },

    # ─── RETARD INTERVENTION / DELAYED RESPONSE ───────────────────────
    "retard": {
        "aliases": [
            "retard", "ta2khir", "تأخر", "تأخير", "delay", "delayed",
            "retard d'intervention", "late response", "en retard",
            "ta2khir fi tadakhkhol",
        ],
        "meaning": "retard",
        "category_hint": "retard_intervention",
    },
    "personne venu": {
        "aliases": [
            "7ata wa7ed ma ja", "ma ja 7ad", "ma jech 7ad",
            "3ayetlkom w 7ata wa7ed ma ja", "حتى واحد ما جا",
            "عيطنالكم وحتى واحد ما جا", "ما جاش حد",
            "nobody came", "no one came", "personne n'est venu",
            "aucune intervention", "pas d'intervention",
            "لا زلنا ننتظرو", "ma jaw 7atta", "ma jach 7add",
        ],
        "meaning": "personne n'est intervenu",
        "category_hint": "retard_intervention",
    },
    "reclamation sans suite": {
        "aliases": [
            "réclamation sans suite", "aucune réponse",
            "aucune reponse", "no response", "no reply",
            "ma jawbouch", "ما جاوبوش", "ignored",
            "sans réponse", "pas de réponse", "حتى جواب",
        ],
        "meaning": "réclamation sans réponse",
        "category_hint": "retard_intervention",
    },
    "appel": {
        "aliases": [
            "3ayet", "aayet", "عيطت", "عيطنا", "عيطتلكم",
            "3ayetlhom", "3ayetlkom", "j'ai appelé",
            "called", "phone call", "appel téléphonique",
            "numero vert", "numéro vert", "الرقم الأخضر",
        ],
        "meaning": "appel / contact",
        "category_hint": "retard_intervention",
    },

    # ─── FÉLICITATION / POSITIVE FEEDBACK ─────────────────────────────
    "merci": {
        "aliases": [
            "choukran", "chokran", "شكرا", "شكرًا",
            "thank you", "thanks", "merci beaucoup",
            "ya3tikom essa7a", "ya3tik essa7a", "يعطيكم الصحة",
            "ya3tik sa7a",
        ],
        "meaning": "merci",
        "category_hint": "felicitation",
    },
    "bravo": {
        "aliases": [
            "bravo", "bravou", "براڤو", "excellent", "ممتاز",
            "bien fait", "good job", "well done", "great",
            "magnifique", "super",
        ],
        "meaning": "bravo",
        "category_hint": "felicitation",
    },
    "satisfait": {
        "aliases": [
            "content", "satisfait", "satisfaite", "happy", "satisfied",
            "راضي", "راضية", "merta7", "مرتاح",
            "el 5edma behya", "service was good",
        ],
        "meaning": "satisfait",
        "category_hint": "felicitation",
    },
    "rapide": {
        "aliases": [
            "rapide", "vite", "fast", "quick", "سريع",
            "fissa", "fi waqt", "بسرعة", "sur3a",
            "réponse rapide", "quick response",
        ],
        "meaning": "rapide",
        "category_hint": "felicitation",
    },
    "professionnel": {
        "aliases": [
            "professionnel", "professional", "محترف", "متخصص",
            "compétent", "efficace", "efficient",
        ],
        "meaning": "professionnel",
        "category_hint": "felicitation",
    },
    "bon service": {
        "aliases": [
            "el 5edma behya", "service behi", "good service",
            "خدمة باهية", "خدمة ممتازة", "bon service",
            "service excellent",
        ],
        "meaning": "bon service",
        "category_hint": "felicitation",
    },

    # ─── SUGGESTION ───────────────────────────────────────────────────
    "suggestion": {
        "aliases": [
            "iqtira7", "اقتراح", "suggestion", "propose", "idea",
            "فكرة", "عندي فكرة", "3andi fikra",
        ],
        "meaning": "suggestion",
        "category_hint": "suggestion",
    },
    "ameliorer": {
        "aliases": [
            "améliorer", "improve", "ta7sin", "تحسين",
            "upgrade", "better", "mieux", "moderniser",
            "7asnou", "حسنو",
        ],
        "meaning": "améliorer",
        "category_hint": "suggestion",
    },
    "application": {
        "aliases": [
            "app", "appli", "application", "تطبيق", "التطبيق",
            "mobile app", "l'application",
        ],
        "meaning": "application mobile",
        "category_hint": "suggestion",
    },
    "notification": {
        "aliases": [
            "notification", "alerte", "alert", "sms", "إشعار",
            "تنبيه", "notification sms",
        ],
        "meaning": "notification",
        "category_hint": "suggestion",
    },
    "horaire": {
        "aliases": [
            "horaire", "schedule", "planning", "مواعيد", "جدول",
            "emploi du temps", "el wa9t", "الوقت",
        ],
        "meaning": "horaire / planning",
        "category_hint": "suggestion",
    },

    # ─── ACTIONS / VERBS ──────────────────────────────────────────────
    "signaler": {
        "aliases": [
            "signaler", "report", "إبلاغ", "بلغت", "ballught",
            "ballaghtkom", "بلغتكم", "flag", "je signale",
        ],
        "meaning": "signaler",
        "category_hint": None,
    },
    "reclamer": {
        "aliases": [
            "réclamer", "reclamer", "chakwa", "شكوى", "شكاوي",
            "complaint", "complain", "réclamation", "reclamation",
            "plainte", "el chakwa", "الشكوى","mochkla",
        ],
        "meaning": "réclamer / porter plainte",
        "category_hint": None,
    },
    "reparer": {
        "aliases": [
            "réparer", "reparer", "y3addel", "ya3del","ysala7", "يعدل",
            "fix", "repair", "إصلاح", "يصلح", "يصلحو",
            "sal7ou", "salhou", "صلحو", "salli7", "تصليح",
        ],
        "meaning": "réparer",
        "category_hint": None,
    },
    "remplacer": {
        "aliases": [
            "remplacer", "replace", "baddel", "بدل", "تبديل",
            "changer", "change", "remplacement",
        ],
        "meaning": "remplacer",
        "category_hint": None,
    },
    "installer": {
        "aliases": [
            "installer", "install", "تركيب", "yrakkeb", "ركب",
            "installation", "pose", "poser",
        ],
        "meaning": "installer",
        "category_hint": None,
    },
    "verifier": {
        "aliases": [
            "vérifier", "verifier", "check", "contrôler",
            "inspecter", "inspection", "تحقق", "فحص",
            "chouf", "شوف",
        ],
        "meaning": "vérifier",
        "category_hint": None,
    },
    "intervenir": {
        "aliases": [
            "intervenir", "tadakhkhol", "تدخل", "intervene",
            "intervention", "تدخلو", "tadakhkhlou", "respond",
        ],
        "meaning": "intervenir",
        "category_hint": None,
    },
    "attendre": {
        "aliases": [
            "attendre", "nestanna", "نستنى", "ننتظرو",
            "wait", "waiting", "انتظار", "nstannaw",
        ],
        "meaning": "attendre",
        "category_hint": None,
    },

    # ─── PEOPLE / PERSONNEL ───────────────────────────────────────────
    "technicien": {
        "aliases": [
            "technicien", "fanni", "فني", "الفني", "technician",
            "el fanni", "agent technique", "agent",
        ],
        "meaning": "technicien",
        "category_hint": None,
    },
    "equipe": {
        "aliases": [
            "équipe", "equipe", "fari9", "فريق", "team",
            "el fari9", "équipe technique", "الفريق الفني",
        ],
        "meaning": "équipe",
        "category_hint": None,
    },
    "voisin": {
        "aliases": [
            "jar", "جار", "جيران", "jirane", "voisin", "voisins",
            "neighbor", "neighbours",
        ],
        "meaning": "voisin",
        "category_hint": None,
    },

    # ─── PLACES / LIEUX ───────────────────────────────────────────────
    "maison": {
        "aliases": [
            "dar", "دار", "الدار", "maison", "house", "home",
            "chez moi", "el dar", "bayt", "بيت",
        ],
        "meaning": "maison",
        "category_hint": None,
    },
    "immeuble": {
        "aliases": [
            "3imara", "aimara", "عمارة", "immeuble", "building",
            "apartment building", "bloc",
        ],
        "meaning": "immeuble",
        "category_hint": None,
    },
    "rue": {
        "aliases": [
            "zenqa", "zen9a", "زنقة", "شارع", "نهج",
            "rue", "street", "road", "nahj", "chari3",
        ],
        "meaning": "rue",
        "category_hint": None,
    },
    "quartier": {
        "aliases": [
            "7ouma", "houma", "حومة", "quartier", "neighborhood",
            "zone", "منطقة", "hay", "حي",
        ],
        "meaning": "quartier",
        "category_hint": None,
    },
    "etage": {
        "aliases": [
            "tabe9", "tabq", "طابق", "étage", "floor",
            "el tabe9 el fou9ani", "الطابق العلوي",
        ],
        "meaning": "étage",
        "category_hint": None,
    },

    # ─── ADJECTIVES / DESCRIPTIONS ────────────────────────────────────
    "grand": {
        "aliases": [
            "kbir", "kbiira", "كبير", "كبيرة", "grand", "grande",
            "big", "large", "enormous", "énorme",
        ],
        "meaning": "grand",
        "category_hint": None,
    },
    "petit": {
        "aliases": [
            "sghir", "sghira", "صغير", "صغيرة", "petit", "petite",
            "small", "little",
        ],
        "meaning": "petit",
        "category_hint": None,
    },
    "beaucoup": {
        "aliases": [
            "barcha", "برشة", "yesser", "ياسر", "beaucoup",
            "a lot", "many", "much", "bzf", "بزاف",
            "too much", "trop",
        ],
        "meaning": "beaucoup",
        "category_hint": None,
    },
    "ancien": {
        "aliases": [
            "qdim", "9dim", "قديم", "ancien", "old", "vieux",
            "vetuste", "vétuste", "obsolete",
        ],
        "meaning": "ancien / vétuste",
        "category_hint": None,
    },
    "nouveau": {
        "aliases": [
            "jdid", "جديد", "nouveau", "new", "neuf", "récent",
        ],
        "meaning": "nouveau",
        "category_hint": None,
    },
    "casse": {
        "aliases": [
            "mherres", "m5asra", "مخسّر", "خسارة", "خربان",
            "cassé", "broken", "damaged", "en panne",
            "5arben", "خربان", "m5arben",
        ],
        "meaning": "cassé / en panne",
        "category_hint": None,
    },
    "bon": {
        "aliases": [
            "behi", "باهي", "mzeyen", "مزيان", "bon", "good",
            "bien", "okay", "ok", "correct",
        ],
        "meaning": "bon / bien",
        "category_hint": None,
    },
    "mauvais": {
        "aliases": [
            "khayeb", "5ayeb", "خايب", "mouch behi",
            "mauvais", "bad", "terrible", "awful",
            "mouch mzeyen", "موش مزيان", "موش باهي",
        ],
        "meaning": "mauvais",
        "category_hint": None,
    },

    # ─── TIME / TEMPS ─────────────────────────────────────────────────
    "jour": {
        "aliases": [
            "nhar", "youm", "يوم", "نهار", "jour", "day",
            "jours", "days", "أيام", "ayem", "nharat",
        ],
        "meaning": "jour",
        "category_hint": None,
    },
    "semaine": {
        "aliases": [
            "jom3a", "جمعة", "أسبوع", "semaine", "week",
            "el jom3a", "هالجمعة",
        ],
        "meaning": "semaine",
        "category_hint": None,
    },
    "mois": {
        "aliases": [
            "chaher", "شهر", "mois", "month", "أشهر",
        ],
        "meaning": "mois",
        "category_hint": None,
    },
    "depuis": {
        "aliases": [
            "men", "من", "depuis", "since", "for",
            "mel", "من وقت",
        ],
        "meaning": "depuis",
        "category_hint": None,
    },
    "maintenant": {
        "aliases": [
            "tawa", "توا", "الآن", "maintenant", "now",
            "right now", "immédiatement", "fissa",
        ],
        "meaning": "maintenant",
        "category_hint": None,
    },
    "longtemps": {
        "aliases": [
            "barcha wa9t", "برشة وقت", "ياسر وقت",
            "long time", "longtemps", "depuis longtemps",
            "a long time", "men barcha",
        ],
        "meaning": "longtemps",
        "category_hint": None,
    },

    # ─── URGENCY / URGENCE ────────────────────────────────────────────
    "urgent": {
        "aliases": [
            "urgent", "3ajel", "عاجل", "urgently", "emergency",
            "استعجال", "d'urgence", "très urgent", "ista3jal",
        ],
        "meaning": "urgent",
        "category_hint": None,
    },
    "critique": {
        "aliases": [
            "critique", "critical", "حرج", "حرجة", "خطير",
            "dangerous", "dangereux", "5atir", "khatir",
        ],
        "meaning": "critique / dangereux",
        "category_hint": None,
    },
    "insupportable": {
        "aliases": [
            "insupportable", "unbearable", "intolerable",
            "ma na7milhech", "ما نحملهاش", "inacceptable",
            "c'est trop", "mech normal", "mouch normal",
        ],
        "meaning": "insupportable",
        "category_hint": None,
    },

    # ─── DIRECTIONS / INDICATIONS ─────────────────────────────────────
    "devant": {
        "aliases": [
            "gueddem", "9ddem", "9oddem", "قدام", "devant",
            "in front of", "en face",
        ],
        "meaning": "devant",
        "category_hint": None,
    },
    "derriere": {
        "aliases": [
            "wra", "ورا", "derrière", "behind", "el wra",
        ],
        "meaning": "derrière",
        "category_hint": None,
    },
    "a cote": {
        "aliases": [
            "7dha", "حذا", "جنب", "à côté", "beside", "next to",
            "7dhaya", "janb", "ba7dhe",
        ],
        "meaning": "à côté",
        "category_hint": None,
    },
    "sous terre": {
        "aliases": [
            "ta7t el ardh", "تحت الأرض", "sous terre",
            "underground", "enterré", "souterrain",
            "ta7t lardh", "buried",
        ],
        "meaning": "sous terre / enterré",
        "category_hint": None,
    },

    # ─── PROBLEM-SPECIFIC EXPRESSIONS ─────────────────────────────────
    "chasse d'eau": {
        "aliases": [
            "chasse d'eau", "chasse deau", "sifon", "siphon",
            "سيفون", "toilette", "toilet", "wc",
            "el chasse", "chass deau",
        ],
        "meaning": "chasse d'eau",
        "category_hint": "fuite_visible",
    },
    "goutte": {
        "aliases": [
            "goutte", "drop", "drip", "9atra", "قطرة", "يقطر",
            "dripping", "qui goutte", "y9atter", "ya9tor",
        ],
        "meaning": "goutte à goutte",
        "category_hint": "fuite_visible",
    },
    "trou": {
        "aliases": [
            "trou", "hole", "tho9b", "ثقب", "7ofra", "حفرة",
            "trou dans le tuyau",
        ],
        "meaning": "trou",
        "category_hint": "fuite_visible",
    },
    "rouille": {
        "aliases": [
            "rouille", "rust", "sda", "sdid", "صدأ", "مصدي",
            "rouillé", "rusty", "msadid",
        ],
        "meaning": "rouille",
        "category_hint": "qualite_eau",
    },
    "calcaire": {
        "aliases": [
            "calcaire", "limestone", "kils", "كلس", "tartre",
            "dépôt calcaire", "pierre",
        ],
        "meaning": "calcaire / tartre",
        "category_hint": "qualite_eau",
    },

    # ─── SONEDE-SPECIFIC ──────────────────────────────────────────────
    "sonede": {
        "aliases": [
            "sonede", "la sonede", "soned", "الصوندة", "صوندة",
            "SONEDE", "el sonede",
        ],
        "meaning": "SONEDE",
        "category_hint": None,
    },
    "agence": {
        "aliases": [
            "agence", "wikala", "وكالة", "agency", "bureau",
            "agence sonede", "agence locale", "el wikala", "el agence",
        ],
        "meaning": "agence",
        "category_hint": None,
    },
    "abonnement": {
        "aliases": [
            "abonnement", "ishtirak", "اشتراك", "subscription",
            "contrat", "contract", "عقد",
        ],
        "meaning": "abonnement / contrat",
        "category_hint": "facturation",
    },
    "branchement": {
        "aliases": [
            "branchement", "raccordement", "connection",
            "rabt", "ربط", "توصيل", "tawsil",
            "branchement neuf", "nouveau branchement",
        ],
        "meaning": "branchement / raccordement",
        "category_hint": None,
    },

    # ─── ADDITIONAL WATER QUALITY ─────────────────────────────────────
    "mousse": {
        "aliases": [
            "mousse", "foam", "رغوة", "raghwa", "bubbly",
            "bulles", "foamy water",
        ],
        "meaning": "eau mousseuse",
        "category_hint": "qualite_eau",
    },
    "sable": {
        "aliases": [
            "sable", "sand", "رمل", "raml", "sandy water",
            "el ma fih raml",
        ],
        "meaning": "sable dans l'eau",
        "category_hint": "qualite_eau",
    },
    "vers": {
        "aliases": [
            "vers", "ver", "worm", "worms", "دود", "doud",
            "insectes", "insects", "حشرات",
        ],
        "meaning": "vers / insectes dans l'eau",
        "category_hint": "qualite_eau",
    },
    "soufre": {
        "aliases": [
            "soufre", "sulfur", "كبريت", "kibrit",
            "odeur de soufre", "ri7et kibrit",
            "sulfur smell", "rotten egg smell",
        ],
        "meaning": "odeur de soufre",
        "category_hint": "qualite_eau",
    },

    # ─── ADDITIONAL BILLING ───────────────────────────────────────────
    "estimation": {
        "aliases": [
            "estimation", "estimate", "تقدير", "ta9dir",
            "facture estimée", "estimated bill",
        ],
        "meaning": "estimation / facture estimée",
        "category_hint": "facturation",
    },
    "penalite": {
        "aliases": [
            "pénalité", "penalite", "penalty", "amende",
            "fine", "غرامة", "gharama",
        ],
        "meaning": "pénalité / amende",
        "category_hint": "facturation",
    },

    # ─── ADDITIONAL URGENCY EXPRESSIONS ───────────────────────────────
    "sans preavis": {
        "aliases": [
            "sans préavis", "sans preavis", "without warning",
            "بلا سابق إعلام", "bla sabe9 i3lam",
            "without notice", "sans avertissement",
            "bla ma y9oulou", "بلا ما يقولو",
        ],
        "meaning": "sans préavis",
        "category_hint": "coupure_non_signalee",
    },
    "catastrophe": {
        "aliases": [
            "catastrophe", "disaster", "كارثة", "karitha",
            "catastrophique",
        ],
        "meaning": "catastrophe",
        "category_hint": None,
    },

    # ─── ADDITIONAL INFRASTRUCTURE ────────────────────────────────────
    "regard": {
        "aliases": [
            "regard", "manhole", "bouche d'égout",
            "فتحة التفقد", "ghota", "غطاء",
        ],
        "meaning": "regard / bouche d'égout",
        "category_hint": None,
    },
    "borne fontaine": {
        "aliases": [
            "borne fontaine", "fontaine", "fountain",
            "نافورة", "sabbala", "سبالة",
        ],
        "meaning": "borne fontaine",
        "category_hint": None,
    },
    "chateau d'eau": {
        "aliases": [
            "château d'eau", "chateau deau", "water tower",
            "برج الماء", "borj el ma",
        ],
        "meaning": "château d'eau",
        "category_hint": None,
    },
    "egout": {
        "aliases": [
            "égout", "egout", "sewer", "drain",
            "baloua", "بالوعة", "مجاري", "majari",
        ],
        "meaning": "égout",
        "category_hint": None,
    },

    # ─── ADDITIONAL ACTIONS ───────────────────────────────────────────
    "couper": {
        "aliases": [
            "couper", "9at3ou", "قطعو", "cut", "shut off",
            "fermer", "ghla9", "أغلقو",
        ],
        "meaning": "couper l'eau",
        "category_hint": "coupure_non_signalee",
    },
    "ouvrir": {
        "aliases": [
            "ouvrir", "7all", "حل", "open", "turn on",
            "iftah", "افتح", "remettez",
        ],
        "meaning": "ouvrir / remettre l'eau",
        "category_hint": None,
    },
    "verser": {
        "aliases": [
            "couler", "verser", "ysib", "يسيب", "يصب",
            "flow", "pour", "el ma ysib",
        ],
        "meaning": "couler / verser",
        "category_hint": None,
    },

    # ─── MISC / GENERAL ──────────────────────────────────────────────
    "probleme": {
        "aliases": [
            "moshkil", "mochkla", "mushkila", "مشكل", "مشكلة", "problème",
            "problem", "issue", "el moshkil", "المشكل",
            "souci", "panne",
        ],
        "meaning": "problème",
        "category_hint": None,
    },
    "solution": {
        "aliases": [
            "solution", "7all", "حل", "resolve", "résoudre",
            "7ellouh", "حلوها",
        ],
        "meaning": "solution",
        "category_hint": None,
    },
    "aide": {
        "aliases": [
            "aide", "help", "مساعدة", "3awnouni", "عاونوني",
            "assistance", "secours",
        ],
        "meaning": "aide",
        "category_hint": None,
    },
    "danger": {
        "aliases": [
            "danger", "5atar", "خطر", "dangerous", "dangereux",
            "risk", "risque",
        ],
        "meaning": "danger",
        "category_hint": None,
    },
    "enfants": {
        "aliases": [
            "sghar", "صغار", "أطفال", "enfants", "children", "kids",
            "awled", "أولاد", "el sghar",
        ],
        "meaning": "enfants",
        "category_hint": None,
    },
    "famille": {
        "aliases": [
            "3ayla", "عائلة", "عيلة", "famille", "family",
            "3aylet", "el 3ayla",
        ],
        "meaning": "famille",
        "category_hint": None,
    },
    "photo": {
        "aliases": [
            "photo", "taswira", "صورة", "تصويرة", "image",
            "picture", "pic",
        ],
        "meaning": "photo",
        "category_hint": None,
    },
    "sonede merci": {
        "aliases": [
            "merci sonede", "thanks sonede", "شكرا الصوند",
            "sonede bravo", "bravo sonede",
            "شكرا للفريق الفني", "merci à l'équipe",
        ],
        "meaning": "remerciement SONEDE",
        "category_hint": "felicitation",
    },
    "sante": {
        "aliases": [
            "santé", "se77a", "health", "صحة", "el sa77a",
            "risque sanitaire", "health risk",
        ],
        "meaning": "santé",
        "category_hint": None,
    },
    "puits": {
        "aliases": [
            "puits", "bir", "بئر", "well", "forage", "borehole",
        ],
        "meaning": "puits",
        "category_hint": None,
    },
    "coupure repetee": {
        "aliases": [
            "coupure répétée", "coupures répétées",
            "repeated cuts", "قطع متكرر", "9at3 metkarrer",
            "encore une coupure", "again", "3awed 9at3ou",
        ],
        "meaning": "coupure d'eau répétée",
        "category_hint": "coupure_non_signalee",
    },
    "fuite route": {
        "aliases": [
            "fuite sur la route", "fuite dans la rue",
            "leak on the road", "el ma ysib fel trig",
            "الماء يسيب في الطريق", "el ma yji fel zanqa",
        ],
        "meaning": "fuite visible sur la voie publique",
        "category_hint": "fuite_visible",
    },
    "bouillonnement": {
        "aliases": [
            "bouillonnement", "jaillissement", "geyser",
            "el ma yetfawwar", "الماء يتفور", "water gushing",
            "water spraying",
        ],
        "meaning": "bouillonnement / jaillissement",
        "category_hint": "fuite_visible",
    },
    "renovation": {
        "aliases": [
            "rénovation", "renovation", "tajdid", "تجديد",
            "travaux de rénovation", "renewal",
        ],
        "meaning": "rénovation du réseau",
        "category_hint": "suggestion",
    },
    "chaleur": {
        "aliases": [
            "chaleur", "s5ouna", "heat", "حرارة", "سخونة",
            "eau chaude", "hot water", "el ma s5oun",
        ],
        "meaning": "eau chaude / problème de température",
        "category_hint": "qualite_eau",
    },
    "gaspillage": {
        "aliases": [
            "gaspillage", "waste", "tabdhir", "تبذير", "إهدار",
            "wasting water", "gaspiller",
        ],
        "meaning": "gaspillage",
        "category_hint": None,
    },
    "coupure nocturne": {
        "aliases": [
            "coupure la nuit", "coupure nocturne", "night cut",
            "9at3 bellil", "قطع بالليل", "el ma y9os bellil",
            "pas d'eau la nuit",
        ],
        "meaning": "coupure d'eau la nuit",
        "category_hint": "coupure_non_signalee",
    },
    "matin": {
        "aliases": [
            "matin", "sba7", "صباح", "morning", "le matin",
            "fi sba7", "في الصباح",
        ],
        "meaning": "matin",
        "category_hint": None,
    },
    "soir": {
        "aliases": [
            "soir", "3shiya", "عشية", "evening", "le soir",
            "bellil", "بالليل", "night",
        ],
        "meaning": "soir / nuit",
        "category_hint": None,
    },
    "heures de pointe": {
        "aliases": [
            "heures de pointe", "peak hours", "sa3at el dhora",
            "ساعات الذروة", "peak time",
        ],
        "meaning": "heures de pointe",
        "category_hint": "pression_faible",
    },
    "nettoyage": {
        "aliases": [
            "nettoyage", "tandhif", "cleaning", "تنظيف",
            "nettoyer", "clean", "nadhfou",
        ],
        "meaning": "nettoyage",
        "category_hint": None,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# 3. URGENCY MARKERS
# ═══════════════════════════════════════════════════════════════════════
URGENCY_MARKERS = [
    # French
    "depuis 2 jours", "depuis 3 jours", "depuis des jours",
    "depuis une semaine", "depuis plusieurs jours", "depuis 10 jours",
    "sans preavis", "sans préavis", "aucune reponse", "aucune réponse",
    "urgent", "critique", "catastrophe", "danger", "insupportable",
    "c'est grave", "très grave",
    # Derja Latin
    "men 3 jours", "mel 48 heures", "mel 5 ayem", "men yomein",
    "men youmain", "mel yom el awal", "tawa yehrab", "tawa yhrab",
    "barcha wa9t", "5ater 3 jours", "3la 5ater barcha wa9t",
    "mouch normal", "mech normal", "el wad3 5atir",
    # Arabic
    "من يومين", "من ثلاثة أيام", "من عدة أيام", "بلا سابق إعلام",
    "حتى جواب", "عاجل", "خطير", "توا يهرب", "ياسر وقت",
    "كارثة", "خطر", "لازمني مساعدة",
    # English
    "for days", "emergency", "critical", "no response",
    "for a week", "very urgent", "need help",
]


# ═══════════════════════════════════════════════════════════════════════
# 4. LOOKUP FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def _build_alias_map():
    """Pre-compute a flat mapping: alias (lowercased) → canonical form.
    Sorted by descending length for greedy matching."""
    mapping = {}
    for canonical, info in DERJA_DICT.items():
        for alias in info["aliases"]:
            key = alias.lower().strip()
            if key and key != canonical:
                mapping[key] = canonical
    return mapping


_ALIAS_MAP = _build_alias_map()
# Sort once by length descending — greedy matching
_SORTED_ALIASES = sorted(_ALIAS_MAP.keys(), key=len, reverse=True)


def normalize_derja(text: str) -> str:
    """Replace known Derja aliases with their canonical (French) form.
    Works on already-lowercased text after apply_char_substitutions().
    Uses greedy longest-match-first to avoid partial replacements."""
    for alias in _SORTED_ALIASES:
        if alias in text:
            text = text.replace(alias, _ALIAS_MAP[alias])
    return text


def analyze_dialect(text: str) -> dict:
    """
    Cherche les expressions Derja connues dans un texte déjà normalisé
    (voir preprocessing.normalize_text).

    Retourne :
    {
        "matches": [
            {"expression": "el mé tay7", "meaning_fr": "...", "category_hint": "pression_faible"},
            ...
        ],
        "category_hints": ["pression_faible", ...],   # dédupliqué
        "urgency_signal": bool
    }
    """
    if not text:
        return {"matches": [], "category_hints": [], "urgency_signal": False}

    t = text.lower()
    matches = []
    seen_hints = []

    for canonical, info in DERJA_DICT.items():
        all_forms = [canonical] + info["aliases"]
        for form in all_forms:
            if form.lower() in t:
                matches.append({
                    "expression": form,
                    "meaning_fr": info["meaning"],
                    "category_hint": info.get("category_hint"),
                })
                hint = info.get("category_hint")
                if hint and hint not in seen_hints:
                    seen_hints.append(hint)
                break  # one match per entry

    urgency_signal = any(marker in t for marker in URGENCY_MARKERS)

    return {
        "matches": matches,
        "category_hints": seen_hints,
        "urgency_signal": urgency_signal,
    }
