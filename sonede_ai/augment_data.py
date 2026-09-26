import pandas as pd
import numpy as np
import random
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'sonede_complaints_dataset.csv')

df = pd.read_csv(DATA_PATH)

def augment_text(text, lang):
    text = str(text)
    prefixes_fr = ["Bonjour, ", "Urgent: ", "Problème: ", "Svp, ", "Je signale que "]
    prefixes_ar = ["السلام عليكم، ", "عاجل: ", "مشكلة: ", "الرجاء التدخل، ", "أبلغ عن "]
    prefixes_tn = ["Billehi ", "Aman ", "Urgent ", "Belehi ", "Choufouna hal "]
    
    if lang == "fr":
        return random.choice(prefixes_fr) + text.lower()
    elif lang in ["ar", "tn_arabe"]:
        return random.choice(prefixes_ar) + text
    else:
        return random.choice(prefixes_tn) + text.lower()

augmented_rows = []
for _, row in df.iterrows():
    new_row = row.copy()
    new_row['id_plainte'] = str(new_row['id_plainte']) + "_AUG"
    new_row['texte_plainte'] = augment_text(row['texte_plainte'], row['langue'])
    augmented_rows.append(new_row)

df_aug = pd.DataFrame(augmented_rows)

df_final = pd.concat([df, df_aug], ignore_index=True)
df_final.to_csv(DATA_PATH, index=False)

print(f"Data augmented successfully! New size: {len(df_final)} rows.")
