import spacy
import pandas as pd
import pycountry

nlp = spacy.load("en_core_web_sm")

def is_country(name):
    try:
        pycountry.countries.lookup(name)
        return True
    except LookupError:
        return False

def extract_entities(texts):
    rows = []
    for doc_id, text in enumerate(texts):
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("GPE", "ORG"):
                rows.append({
                    "doc_id": doc_id,
                    "entity": ent.text,
                    "label": ent.label_,
                    "is_country": ent.label_ == "GPE" and is_country(ent.text),
                })
    return pd.DataFrame(rows)

if __name__ == "__main__":
    texts = [
        "Foxconn assembles iPhones in China and ships them to Germany.",
        "Tata Steel imports coal from Australia for its India plant.",
    ]
    df = extract_entities(texts)
    print(df)

    countries = df[df["is_country"]]
    print(countries.groupby("entity").size().sort_values(ascending=False))

    df.to_csv("entities.csv", index=False)