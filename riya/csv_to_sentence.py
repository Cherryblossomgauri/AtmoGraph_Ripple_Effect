import pandas as pd

CSV_FILE = "shipments.csv"    
TEXT_COLUMN = "description"   

df = pd.read_csv(CSV_FILE, encoding="utf-8")
sentences = df[TEXT_COLUMN].dropna().astype(str).str.strip()

count = 0
with open("supply_sentences.txt", "w", encoding="utf-8") as f:
    for s in sentences:
        if s:
            f.write(s.replace("\n", " ") + "\n")
            count += 1
print(f"{count} sentences written to supply_sentences.txt")