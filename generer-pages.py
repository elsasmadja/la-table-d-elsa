# -*- coding: utf-8 -*-
"""
Génère une page HTML par recette, pour que Google puisse les référencer.

À relancer après chaque ajout de recette :   python generer-pages.py

Le script lit index.html, en extrait les recettes, et écrit :
  recettes/<nom-de-la-recette>.html   une page par recette
  recettes/index.html                 le sommaire
  sitemap.xml                         la liste des pages pour Google
  robots.txt                          l'autorisation d'exploration
"""
import re, json, html, os, subprocess, unicodedata
from datetime import date

SITE = "https://latabledelsa.fr"
RACINE = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(RACINE, "recettes")

# ── 1. Extraire les recettes depuis index.html ───────────────────────────
def lire_recettes():
    s = open(os.path.join(RACINE, "index.html"), encoding="utf-8").read()
    js = re.findall(r"<script>(.*?)</script>", s, re.S)[1]
    coeur = js[: js.index("function openModal(")]
    script = coeur + """
const out={};
Object.keys(recipes).forEach(id=>{
  const r=recipes[id];
  out[id]={titre:r.title, tag:r.tag, kcal:r.kcal, portions:r.portions,
           prot:r.proteines, gluc:r.glucides, lip:r.lipides,
           chapo:r.chapo||'', astuce:r.astuce||'',
           ingredients:r.ingredients||[],
           steps:(r.steps||[]).map(x=>typeof x==='string'?x:x.text),
           photos:(IMGS[id]||[]).filter(x=>x.indexOf('data:')!==0)};
});
console.log(JSON.stringify(out));
"""
    open("/tmp/_extraction.js", "w", encoding="utf-8").write(script)
    sortie = subprocess.run(["node", "/tmp/_extraction.js"], capture_output=True, text=True)
    if sortie.returncode != 0:
        raise SystemExit("Extraction impossible :\n" + sortie.stderr[:500])
    return json.loads(sortie.stdout)

def sans_accent(t):
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")

def adresse(titre):
    t = sans_accent(titre.lower()).replace("’", "").replace("'", "")
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t + ".html"

def e(t):
    return html.escape(str(t), quote=True)

# ── 2. Les données structurées, que Google lit pour ses résultats enrichis ──
def duree_iso(portions_jours, steps):
    jours = 0
    for st in steps:
        m = re.match(r"\s*J-(\d+)", st)
        if m:
            jours = max(jours, int(m.group(1)))
    return "P{}D".format(jours + 1) if jours else "PT1H"

def parts(portions):
    m = re.search(r"/\s*(\d+)", portions or "")
    if m:
        return m.group(1)
    m = re.match(r"\s*(\d+)", portions or "")
    return m.group(1) if m else "8"

def donnees_structurees(rid, r):
    ing = [x for x in r["ingredients"] if not (x.startswith("— ") and x.endswith(" —"))]
    d = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": r["titre"],
        "description": r["chapo"] or "Recette maison testée et approuvée sur La Table d'Elsa.",
        "image": [SITE + "/" + p for p in r["photos"][:2]],
        "author": {"@type": "Person", "name": "Elsa Smadja"},
        "datePublished": date.today().isoformat(),
        "recipeCategory": r["tag"].split("·")[0].strip(),
        "recipeCuisine": "Française",
        "recipeYield": parts(r["portions"]) + " parts",
        "totalTime": duree_iso(r["portions"], r["steps"]),
        "recipeIngredient": ing,
        "recipeInstructions": [
            {"@type": "HowToStep", "position": i + 1,
             "text": re.sub(r"^\s*(Jour J|J-\d)\s*[—–-]\s*", "", st)}
            for i, st in enumerate(r["steps"])
        ],
        "nutrition": {
            "@type": "NutritionInformation",
            "calories": "{} kcal".format(r["kcal"]),
            "proteinContent": "{} g".format(r["prot"]),
            "carbohydrateContent": "{} g".format(r["gluc"]),
            "fatContent": "{} g".format(r["lip"]),
            "servingSize": "1 part",
        },
        "inLanguage": "fr-FR",
    }
    return json.dumps(d, ensure_ascii=False, indent=2)

# ── 3. Le gabarit d'une page ────────────────────────────────────────────
STYLE = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#F7F3EC;color:#2E2A25;font-family:Jost,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.7;font-weight:300}
.enveloppe{max-width:760px;margin:0 auto;padding:2rem 1.4rem 5rem}
.retour{display:inline-block;font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;color:#8B6347;text-decoration:none;margin-bottom:2rem}
.retour:hover{text-decoration:underline}
.photo{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:12px;margin-bottom:1.6rem;background:#EDE7DA}
.tag{font-size:0.66rem;letter-spacing:0.14em;text-transform:uppercase;color:#C4A882;font-weight:500;text-align:center}
h1{font-family:'Cormorant Garamond',Georgia,serif;font-size:2.6rem;font-weight:400;text-align:center;margin:0.5rem 0 0.6rem;line-height:1.1}
.chapo{font-family:'Cormorant Garamond',Georgia,serif;font-style:italic;font-size:1.2rem;color:#7A6F63;text-align:center;margin-bottom:1.6rem}
.reperes{display:flex;border-top:1px solid #EDE7DA;border-bottom:1px solid #EDE7DA;padding:1rem 0;margin-bottom:2rem;flex-wrap:wrap}
.repere{flex:1;min-width:110px;padding:0 0.9rem;border-left:1px solid #EDE7DA}
.repere:first-child{border-left:none;padding-left:0}
.repere b{display:block;font-family:'Cormorant Garamond',Georgia,serif;font-size:1.6rem;font-weight:400}
.repere span{font-size:0.6rem;letter-spacing:0.12em;text-transform:uppercase;color:#C4A882;font-weight:500}
h2{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.8rem;font-weight:400;margin:2.2rem 0 1rem}
ul.ingredients{list-style:none}
ul.ingredients li{padding:0.35rem 0;border-bottom:1px dashed #EDE7DA;font-size:0.94rem;color:#5A5248}
ul.ingredients li.section{border:none;padding-top:1.2rem;font-size:0.66rem;letter-spacing:0.13em;text-transform:uppercase;font-weight:600;color:#4E6E52}
ol.etapes{list-style:none;counter-reset:e}
ol.etapes li{counter-increment:e;position:relative;padding:0 0 1.4rem 3rem;font-size:0.96rem;color:#5A5248}
ol.etapes li::before{content:counter(e);position:absolute;left:0;top:-0.3rem;font-family:'Cormorant Garamond',Georgia,serif;font-size:1.9rem;color:#C4A882}
.astuce{background:#FDFAF6;border-left:3px solid #7A9E7E;border-radius:6px;padding:1rem 1.2rem;margin-top:2rem;font-size:0.92rem;color:#5A5248}
.astuce b{display:block;font-size:0.62rem;letter-spacing:0.13em;text-transform:uppercase;color:#4E6E52;margin-bottom:0.3rem}
.cta{display:block;text-align:center;background:#4E6E52;color:#FDFAF6;text-decoration:none;border-radius:26px;padding:0.95rem;margin-top:2.4rem;font-size:0.7rem;letter-spacing:0.13em;text-transform:uppercase;font-weight:500}
footer{text-align:center;margin-top:2.4rem;font-size:0.72rem;color:#C4A882}
footer a{color:#8B6347}
@media(max-width:560px){h1{font-size:2rem}.enveloppe{padding:1.4rem 1.1rem 3rem}}
"""

def page(rid, r, fichier):
    url = "{}/recettes/{}".format(SITE, fichier)
    photo = SITE + "/" + r["photos"][0] if r["photos"] else ""
    desc = r["chapo"] or "{} — {} kcal par part. Recette détaillée, ingrédients et étapes.".format(r["titre"], r["kcal"])

    ing = ""
    for x in r["ingredients"]:
        if x.startswith("— ") and x.endswith(" —"):
            ing += '<li class="section">{}</li>\n'.format(e(x.strip("— ").strip()))
        else:
            ing += "<li>{}</li>\n".format(e(x))

    etapes = "".join("<li>{}</li>\n".format(e(re.sub(r"^\s*(Jour J|J-\d)\s*[—–-]\s*", "", st)))
                     for st in r["steps"])

    return """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titre} — La Table d'Elsa</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{titre} — La Table d'Elsa">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{photo}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="La Table d'Elsa">
<meta property="og:locale" content="fr_FR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{titre} — La Table d'Elsa">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{photo}">
<link rel="icon" href="../images/icon-192.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>{style}</style>
<script type="application/ld+json">
{jsonld}
</script>
</head>
<body>
<article class="enveloppe">
  <a class="retour" href="../">&larr; La Table d'Elsa</a>
  {img}
  <div class="tag">{tag}</div>
  <h1>{titre}</h1>
  {chapo}
  <div class="reperes">
    <div class="repere"><b>{kcal}</b><span>kcal / part</span></div>
    <div class="repere"><b>{parts}</b><span>parts</span></div>
    <div class="repere"><b>{prot} g</b><span>protéines</span></div>
    <div class="repere"><b>{gluc} g</b><span>glucides</span></div>
  </div>
  <h2>Ingrédients</h2>
  <ul class="ingredients">
{ing}  </ul>
  <h2>Préparation</h2>
  <ol class="etapes">
{etapes}  </ol>
  {astuce}
  <a class="cta" href="../">Voir cette recette en mode cuisine</a>
  <footer>Une recette de <a href="../">La Table d'Elsa</a></footer>
</article>
</body>
</html>
""".format(
        titre=e(r["titre"]), desc=e(desc), url=url, photo=photo, style=STYLE,
        jsonld=donnees_structurees(rid, r), tag=e(r["tag"]),
        img='<img class="photo" src="../{}" alt="{}">'.format(r["photos"][0], e(r["titre"])) if r["photos"] else "",
        chapo='<p class="chapo">{}</p>'.format(e(r["chapo"])) if r["chapo"] else "",
        kcal=r["kcal"], parts=parts(r["portions"]), prot=e(r["prot"]), gluc=e(r["gluc"]),
        ing=ing, etapes=etapes,
        astuce='<div class="astuce"><b>L\'astuce d\'Elsa</b>{}</div>'.format(e(r["astuce"])) if r["astuce"] else "",
    )

def sommaire(pages):
    liens = "".join(
        '<li><a href="{}">{}</a> <span>{} kcal / part</span></li>\n'.format(f, e(t), k)
        for f, t, k in sorted(pages, key=lambda x: x[1])
    )
    return """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Toutes les recettes — La Table d'Elsa</title>
<meta name="description" content="Les {n} recettes de La Table d'Elsa : pâtisserie, goûter, salé, viennoiserie. Ingrédients, étapes et valeurs nutritionnelles.">
<link rel="canonical" href="{site}/recettes/">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@300;400;500&display=swap" rel="stylesheet">
<style>{style}
ul.sommaire{{list-style:none}}
ul.sommaire li{{padding:0.7rem 0;border-bottom:1px solid #EDE7DA;display:flex;justify-content:space-between;align-items:baseline;gap:1rem;flex-wrap:wrap}}
ul.sommaire a{{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.3rem;color:#2E2A25;text-decoration:none}}
ul.sommaire a:hover{{color:#4E6E52}}
ul.sommaire span{{font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;color:#C4A882}}
</style>
</head>
<body>
<div class="enveloppe">
  <a class="retour" href="../">&larr; La Table d'Elsa</a>
  <h1>Toutes les recettes</h1>
  <p class="chapo">{n} recettes testées, retestées, et partagées.</p>
  <ul class="sommaire">
{liens}  </ul>
</div>
</body>
</html>
""".format(n=len(pages), site=SITE, style=STYLE, liens=liens)

# ── 4. Écriture ─────────────────────────────────────────────────────────
def main():
    recettes = lire_recettes()
    os.makedirs(SORTIE, exist_ok=True)
    pages = []
    for rid, r in recettes.items():
        if not r["steps"]:
            continue
        f = adresse(r["titre"])
        open(os.path.join(SORTIE, f), "w", encoding="utf-8").write(page(rid, r, f))
        pages.append((f, r["titre"], r["kcal"]))

    open(os.path.join(SORTIE, "index.html"), "w", encoding="utf-8").write(sommaire(pages))

    aujourdhui = date.today().isoformat()
    urls = ['<url><loc>{}/</loc><lastmod>{}</lastmod><priority>1.0</priority></url>'.format(SITE, aujourdhui),
            '<url><loc>{}/recettes/</loc><lastmod>{}</lastmod><priority>0.8</priority></url>'.format(SITE, aujourdhui)]
    urls += ['<url><loc>{}/recettes/{}</loc><lastmod>{}</lastmod><priority>0.7</priority></url>'.format(SITE, f, aujourdhui)
             for f, _, _ in pages]
    open(os.path.join(RACINE, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join("  " + u for u in urls) + "\n</urlset>\n")

    open(os.path.join(RACINE, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\n\nSitemap: {}/sitemap.xml\n".format(SITE))

    print("{} pages écrites dans recettes/".format(len(pages)))
    print("sitemap.xml et robots.txt mis à jour")

if __name__ == "__main__":
    main()
