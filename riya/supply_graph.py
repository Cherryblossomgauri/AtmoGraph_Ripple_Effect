import json
from collections import Counter
import spacy
import pycountry

nlp = spacy.load("en_core_web_sm")

SUPPLY_VERBS = {"supply", "export", "ship", "send", "deliver", "sell"}
BUY_VERBS = {"import", "buy", "source", "receive"}

# Products that spaCy may tag as companies. These are skipped so they
# don't become nodes. Add more product names here if they show up.
IGNORE = {
    "iphones", "iphone", "phones", "laptops", "electronics", "machinery",
    "textiles", "cars", "steel", "coal", "semiconductors", "chips",
    "memory chips", "machines", "iron ore", "iron", "ore",
}


def normalize(name):
    name = name.strip()
    if name.lower().startswith("the "):
        name = name[4:]
    try:
        return pycountry.countries.lookup(name).name
    except LookupError:
        return name


def is_country(name):
    try:
        pycountry.countries.lookup(name)
        return True
    except LookupError:
        return False


def entities_in(tokens, ents):
    found = []
    for tok in tokens:
        for e in ents:
            if e.start <= tok.i < e.end:
                name = normalize(e.text)
                if name.lower() not in IGNORE and name not in found:
                    found.append(name)
    return found


def find_edges(text):
    doc = nlp(text)
    ents = [e for e in doc.ents if e.label_ in ("GPE", "ORG")]
    edges = []
    for verb in doc:
        if verb.lemma_ not in SUPPLY_VERBS | BUY_VERBS:
            continue
        subjects = []
        for c in verb.children:
            if c.dep_ in ("nsubj", "nsubjpass"):
                subjects = entities_in(c.subtree, ents)
        for c in verb.children:
            targets = entities_in(c.subtree, ents)
            if verb.lemma_ in SUPPLY_VERBS:
                if (c.dep_ == "prep" and c.text.lower() == "to") or c.dep_ == "dobj":
                    edges += [(s, t) for s in subjects for t in targets]
            elif verb.lemma_ in BUY_VERBS and c.dep_ == "prep" and c.text.lower() == "from":
                edges += [(t, s) for s in subjects for t in targets]
    return edges


def build_graph(sentences):
    counts = {}
    for sent in sentences:
        for s, t in find_edges(sent):
            if s != t:
                counts[(s, t)] = counts.get((s, t), 0) + 1
    names = sorted({n for pair in counts for n in pair})
    nodes = [{"id": n, "type": "country" if is_country(n) else "company"} for n in names]
    links = [{"source": s, "target": t, "weight": w} for (s, t), w in counts.items()]
    return {"nodes": nodes, "links": links}


if __name__ == "__main__":
    with open("supply_sentences.txt", encoding="utf-8") as f:
        sentences = [line.strip() for line in f if line.strip()]

    graph = build_graph(sentences)

    print("Supply links found:")
    for link in graph["links"]:
        print(f"  {link['source']} -> {link['target']}  (x{link['weight']})")

    print("\nDestinations per supplier:")
    for name, n in Counter(l["source"] for l in graph["links"]).most_common():
        print(f"  {name}: supplies to {n} destination(s)")

    with open("graph.json", "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    print(f"\n{len(graph['nodes'])} nodes, {len(graph['links'])} links saved to graph.json")