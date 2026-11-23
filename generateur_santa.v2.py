import json
import os
import random
import tempfile
import unicodedata
import uuid
import webbrowser
from pathlib import Path
from html import escape

# ==============================================================================
# 1. PARAMETERS
# ==============================================================================

CADEAUX_PAR_RECEVEUR = 1

# Web URL for hosting the pages (no "/" at the end)
URL_GITHUB = "https://batisteall.github.io/secret_santa"

GIVERS = [
    {"nom": "Bat + Pauline", "photo": "bat_pauline.jpg", "couleur": "#d62828"},
    {"nom": "Max + Marine", "photo": "max_marine.jpg", "couleur": "#2a9d8f"},
    {"nom": "Mar + Clement", "photo": "mar_clem.jpg", "couleur": "#e9c46a"},
    {"nom": "Ludivine", "photo": "ludivine.jpg", "couleur": "#f4a261"},
]

RECEIVERS = [
    {"nom": "William", "photo": "william.jpg", "couleur": "#e76f51"},
    {"nom": "Victoire", "photo": "victoire.jpg", "couleur": "#457b9d"},
    {"nom": "Arthur", "photo": "arthur.jpg", "couleur": "#457b9d"},
    {"nom": "Leo", "photo": "leo.jpg", "couleur": "#457b9d"},
]

# Affinités : personnes à ÉVITER si possible pour un donneur .
A_EVITER = {
    "Ludivine": ["William", "Victoire"],
    "Mar + Clement": ["Leo", "Arthur"],
}

# ==============================================================================
# 2. DRAWING ALGORITHM
# ==============================================================================


def piocher_valide(donneur, pool, deja_attribues, a_eviter=(), tolere_evites=False):
  """Retire du pool un receveur valide (pas soi-même, pas de doublon).

  Les personnes à éviter ne sont prises que si tolere_evites vaut True.
  """
  random.shuffle(pool)
  for i, candidat in enumerate(pool):
    if candidat == donneur or candidat in deja_attribues:
      continue
    if candidat in a_eviter and not tolere_evites:
      continue
    return pool.pop(i)
  return None


def tenter_tirage(noms_adultes, noms_enfants, nb_cadeaux, a_eviter):
  """Un essai de tirage. Renvoie les attributions, ou None si bloqué."""
  pool_adultes = noms_adultes * nb_cadeaux
  pool_enfants = noms_enfants * nb_cadeaux
  attributions = {d: [] for d in noms_adultes}

  ordre = noms_adultes[:]
  random.shuffle(ordre)

  # STEP 1 : 1 giver + 1 receiver for every giver
  for d in ordre:
    for pool in (pool_adultes, pool_enfants):
      cible = piocher_valide(d, pool, attributions[d], a_eviter.get(d, ()))
      if cible:
        attributions[d].append(cible)

  # STEP 2 : fill lackers of one receiver
  # first with giver then with receiver
  random.shuffle(ordre)
  for d in ordre:
    while len(attributions[d]) < 2:
      cible = piocher_valide(d, pool_adultes, attributions[d], a_eviter.get(d, ()))
      if not cible:
        cible = piocher_valide(d, pool_enfants, attributions[d], a_eviter.get(d, ()))
      if not cible:
        break
      attributions[d].append(cible)

  # STEP 3 : deal the surplus
  surplus = pool_adultes + pool_enfants
  while surplus:
    donneurs = sorted(
        noms_adultes, key=lambda d: (len(attributions[d]), random.random())
    )
    place = False
    # D'abord sans toucher aux affinités à éviter, puis en dernier recours avec
    for tolere in (False, True):
      for d in donneurs:
        cible = piocher_valide(
            d, surplus, attributions[d], a_eviter.get(d, ()), tolere
        )
        if cible:
          attributions[d].append(cible)
          place = True
          break
      if place:
        break
    if not place:
      return None  # draw failed

  return attributions


def noter(attributions, noms_adultes, noms_enfants, a_eviter):
  """Plus la note est petite, mieux c'est (ordre de priorité de tes règles)."""
  vals = list(attributions.values())
  trop_peu = sum(1 for r in vals if len(r) < 2)
  evites = sum(
      1 for d, r in attributions.items() for x in r if x in a_eviter.get(d, ())
  )
  sans_mix = sum(
      1
      for r in vals
      if not (
          any(x in noms_adultes for x in r) and any(x in noms_enfants for x in r)
      )
  )
  ecart = max(len(r) for r in vals) - min(len(r) for r in vals)
  return (trop_peu, evites, sans_mix, ecart)


def generer_tirage(givers, receivers, nb_cadeaux, a_eviter=None):
  a_eviter = a_eviter or {}
  noms_adultes = [a["nom"] for a in givers]
  noms_enfants = [e["nom"] for e in receivers]
  tous_membres = givers + receivers

  tous_noms = noms_adultes + noms_enfants
  if len(set(tous_noms)) != len(tous_noms):
    raise ValueError("Deux personnes ont le même nom : les prénoms doivent être uniques.")
  if not noms_adultes:
    raise ValueError("Il faut au moins un donneur.")
  for donneur, evites in a_eviter.items():
    for nom in [donneur] + list(evites):
      if nom not in tous_noms:
        raise ValueError(f"A_EVITER : '{nom}' n'existe pas dans les listes (faute de frappe ?).")

  total = len(tous_noms) * nb_cadeaux
  ecart_ideal = 0 if total % len(noms_adultes) == 0 else 1

  meilleur, meilleure_note = None, None
  for _ in range(3000):
    essai = tenter_tirage(noms_adultes, noms_enfants, nb_cadeaux, a_eviter)
    if essai is None:
      continue
    note = noter(essai, noms_adultes, noms_enfants, a_eviter)
    if meilleure_note is None or note < meilleure_note:
      meilleur, meilleure_note = essai, note
      if note == (0, 0, 0, ecart_ideal):
        break  # on ne fera pas mieux

  if meilleur is None:
    raise RuntimeError(
        "Impossible de trouver une combinaison valide sans doublon avec ces"
        " paramètres (trop de cadeaux par rapport au nombre de participants)."
    )

  for d in meilleur:
    random.shuffle(meilleur[d])
  return meilleur, tous_membres


# ==============================================================================
# 3. HTML GENERATION
# ==============================================================================


def generer_html_individuel(donneur, receveurs, tous_membres):
  membres_js = json.dumps(tous_membres, ensure_ascii=False)
  receveurs_js = json.dumps(receveurs, ensure_ascii=False)
  donneur_html = escape(donneur)

  return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secret Santa - {donneur_html} 🎄</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a2f23; color: white; text-align: center; padding: 20px; margin: 0; }}
        h1 {{ color: #f8b229; margin-bottom: 5px; }}
        .wheel-container {{ position: relative; width: 320px; height: 320px; margin: 20px auto; }}
        canvas {{ width: 100%; height: 100%; border-radius: 50%; box-shadow: 0 0 20px rgba(0,0,0,0.5); }}
        .pointer {{ position: absolute; top: -15px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 15px solid transparent; border-right: 15px solid transparent; border-top: 30px solid #e63946; z-index: 10; }}
        button {{ background: #e63946; color: white; border: none; padding: 15px 30px; font-size: 18px; font-weight: bold; border-radius: 30px; cursor: pointer; margin-top: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }}
        button:disabled {{ background: #555; cursor: not-allowed; }}
        .results {{ margin-top: 25px; font-size: 18px; }}
        .card {{ background: rgba(255,255,255,0.1); padding: 12px 15px; border-radius: 15px; margin: 10px auto; max-width: 300px; display: none; align-items: center; gap: 15px; text-align: left; }}
        .card img {{ width: 55px; height: 55px; border-radius: 50%; object-fit: cover; border: 2px solid #f8b229; background: #333; }}
    </style>
</head>
<body>
    <h1>Salut {donneur_html} ! 🎄</h1>
    <p id="subtitle">Tu as <strong>{len(receveurs)} tirage(s)</strong> à effectuer !</p>

    <div class="wheel-container">
        <div class="pointer"></div>
        <canvas id="wheel" width="500" height="500"></canvas>
    </div>

    <button id="spinBtn" onclick="spin()">Lancer le tirage n°1 🎁</button>
    <div class="results" id="resultsContainer"></div>

    <script>
        const membres = {membres_js};
        const cibles = {receveurs_js};

        const canvas = document.getElementById("wheel");
        const ctx = canvas.getContext("2d");
        const arc = (2 * Math.PI) / membres.length;
        let currentAngle = 0;
        let step = 0;

        const container = document.getElementById("resultsContainer");
        cibles.forEach((nom, idx) => {{
            const m = membres.find(x => x.nom === nom);
            const photo = m ? m.photo : "";
            container.innerHTML += `<div id="res${{idx}}" class="card"><img src="${{photo}}"><div><strong>Cadeau n°${{idx + 1}} :</strong><br><span>${{nom}}</span></div></div>`;
        }});

        const images = {{}};
        membres.forEach(m => {{
            const img = new Image();
            img.onload = () => drawWheel();
            img.src = m.photo;
            images[m.nom] = img;
        }});

        // Largeur disponible dans une part de la roue, à une distance "rayon" du centre
        function largeurMax(rayon) {{
            return Math.min(2 * rayon * Math.tan(arc / 2) * 0.9, 400);
        }}

        // Découpe un nom en plusieurs lignes (aux espaces) et réduit la police si besoin
        function mettreEnForme(nom) {{
            const rayonPremiereLigne = 127;
            let resultat = null;
            for (let taille = 20; taille >= 10; taille--) {{
                ctx.font = "bold " + taille + "px sans-serif";
                const interligne = taille * 1.15;
                const lignes = [];
                let ligne = "";
                nom.split(" ").forEach(mot => {{
                    const test = ligne ? ligne + " " + mot : mot;
                    const rayon = rayonPremiereLigne - lignes.length * interligne;
                    if (!ligne || ctx.measureText(test).width <= largeurMax(rayon)) {{
                        ligne = test;
                    }} else {{
                        lignes.push(ligne);
                        ligne = mot;
                    }}
                }});
                lignes.push(ligne);
                const tient = lignes.every((l, i) => ctx.measureText(l).width <= largeurMax(rayonPremiereLigne - i * interligne));
                resultat = {{ taille, interligne, lignes }};
                if (tient) break;
            }}
            return resultat;
        }}
        const mises = membres.map(m => mettreEnForme(m.nom));

        function drawWheel() {{
            ctx.clearRect(0, 0, 500, 500);
            membres.forEach((m, i) => {{
                const angle = currentAngle + i * arc;
                ctx.beginPath();
                ctx.fillStyle = m.couleur;
                ctx.moveTo(250, 250);
                ctx.arc(250, 250, 240, angle, angle + arc);
                ctx.fill();
                ctx.stroke();

                ctx.save();
                ctx.translate(250 + Math.cos(angle + arc / 2) * 175, 250 + Math.sin(angle + arc / 2) * 175);
                ctx.rotate(angle + arc / 2 + Math.PI / 2);
                ctx.fillStyle = "white";
                ctx.font = "bold " + mises[i].taille + "px sans-serif";
                ctx.textAlign = "center";
                mises[i].lignes.forEach((l, k) => {{
                    ctx.fillText(l, 0, 48 + k * mises[i].interligne);
                }});
                if (images[m.nom] && images[m.nom].complete && images[m.nom].naturalWidth !== 0) {{
                    ctx.beginPath();
                    ctx.arc(0, -10, 32, 0, Math.PI * 2);
                    ctx.clip();
                    ctx.drawImage(images[m.nom], -32, -42, 64, 64);
                }}
                ctx.restore();
            }});
        }}

        function spin() {{
            if (step >= cibles.length) return;
            const btn = document.getElementById("spinBtn");
            btn.disabled = true;

            const targetName = cibles[step];
            const targetIndex = membres.findIndex(m => m.nom === targetName);
            const stopAngle = (3 * Math.PI / 2) - (targetIndex * arc) - (arc / 2);
            const totalRotation = (Math.PI * 10) + ((stopAngle - (currentAngle % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI));

            const duration = 3800;
            const start = performance.now();
            const initialAngle = currentAngle;

            function animate(time) {{
                const progress = Math.min((time - start) / duration, 1);
                const easeOut = 1 - Math.pow(1 - progress, 4);
                currentAngle = initialAngle + totalRotation * easeOut;
                drawWheel();
                if (progress < 1) {{
                    requestAnimationFrame(animate);
                }} else {{
                    document.getElementById(`res${{step}}`).style.display = "flex";
                    step++;
                    if (step < cibles.length) {{
                        btn.innerText = `Lancer le tirage n°${{step + 1}} 🎁`;
                        btn.disabled = false;
                    }} else {{
                        btn.style.display = "none";
                        document.getElementById("subtitle").innerText = "Tirage terminé ! Garde bien le secret 🤫";
                    }}
                }}
            }}
            requestAnimationFrame(animate);
        }}

        drawWheel();
    </script>
</body>
</html>
"""


def nom_fichier_sûr(donneur):
  """'Chloé' -> 'chloe' (pas d'accents dans les URL)."""
  ascii_nom = (
      unicodedata.normalize("NFKD", donneur).encode("ascii", "ignore").decode()
  )
  return "".join(c for c in ascii_nom.lower() if c.isalnum()) or "donneur"


# ==============================================================================
# 4. EXECUTION AND WEB DASHBOARD
# ==============================================================================


PAGE_TABLEAU_DE_BORD = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Secret Santa Familial 🎄</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a2f23; color: white; text-align: center; padding: 20px; }
  h1 { color: #f8b229; }
  .alerte { color: #ffd166; margin: 15px auto; max-width: 500px; }
  .consigne { margin: 15px auto; max-width: 500px; }
  button { display: block; margin: 10px auto; width: 320px; padding: 14px; font-size: 16px; font-weight: bold; color: white; background: #e63946; border: none; border-radius: 12px; cursor: pointer; }
  #statut { color: #a8dadc; font-style: italic; margin: 20px; min-height: 1.5em; }
  details { margin: 30px auto; max-width: 500px; text-align: left; }
  summary { cursor: pointer; text-align: center; color: #a8dadc; }
  pre { background: rgba(0,0,0,0.3); padding: 15px; border-radius: 10px; overflow-x: auto; }
</style>
</head>
<body>
  <h1>Fichiers HTML générés ! 🎅</h1>
  <div class="alerte">__ALERTE__</div>
  <div class="consigne">1. Mets les fichiers .html + photos sur ton GitHub.<br>2. Clique sur un bouton pour copier le lien :</div>
  __BOUTONS__
  <div id="statut">En attente...</div>
  <details>
    <summary>🔍 Debug : voir tous les tirages</summary>
    <pre>__DEBUG__</pre>
  </details>
<script>
  async function copier(btn) {
    const lien = btn.dataset.lien;
    const nom = btn.dataset.nom;
    try {
      await navigator.clipboard.writeText(lien);
    } catch (e) {
      const t = document.createElement("textarea");
      t.value = lien;
      document.body.appendChild(t);
      t.select();
      document.execCommand("copy");
      t.remove();
    }
    btn.textContent = "✅ Lien copié pour " + nom;
    document.getElementById("statut").textContent = "Lien de " + nom + " copié !";
  }
</script>
</body>
</html>
"""


def ouvrir_tableau_de_bord(liens, attributions, tous_membres, texte_alerte):
  """Page locale ouverte dans le navigateur (écrite dans le dossier temporaire, jamais à côté des .html)."""
  boutons = "\n  ".join(
      f'<button data-lien="{escape(lien)}" data-nom="{escape(nom)}"'
      f' onclick="copier(this)">📋 Copier le lien de {escape(nom)}</button>'
      for nom, lien in liens.items()
  )

  # Debug : qui donne à qui, et qui reçoit de qui
  lignes = ["QUI DONNE À QUI (⚠️ = affinité à éviter) :"]
  for donneur, receveurs in attributions.items():
    noms = [
        r + (" ⚠️" if r in A_EVITER.get(donneur, []) else "") for r in receveurs
    ]
    lignes.append(f"  {donneur} → {', '.join(noms)}")
  lignes.append("")
  lignes.append("QUI REÇOIT DE QUI :")
  recu = {m["nom"]: [] for m in tous_membres}
  for donneur, receveurs in attributions.items():
    for r in receveurs:
      recu[r].append(donneur)
  for nom, donneurs in recu.items():
    lignes.append(f"  {nom} ← {', '.join(donneurs)}")

  page = (
      PAGE_TABLEAU_DE_BORD.replace("__ALERTE__", escape(texte_alerte).replace("\n", "<br>"))
      .replace("__BOUTONS__", boutons)
      .replace("__DEBUG__", escape("\n".join(lignes)))
  )
  chemin = Path(tempfile.gettempdir()) / "secret_santa_tableau_de_bord.html"
  chemin.write_text(page, encoding="utf-8")
  print("Tableau de bord :", chemin)
  webbrowser.open(chemin.as_uri())


def main():
  attributions, tous_membres = generer_tirage(
      GIVERS, RECEIVERS, CADEAUX_PAR_RECEVEUR, A_EVITER
  )

  dossier_courant = os.path.dirname(os.path.abspath(__file__))
  liens_generes = {}
  for donneur, receveurs in attributions.items():
    code_secret = uuid.uuid4().hex[:8]
    # nom_fichier = f"tirage_{nom_fichier_sûr(donneur)}_{code_secret}.html"
    nom_fichier = f"tirage_{nom_fichier_sûr(donneur)}.html"
    chemin_complet = os.path.join(dossier_courant, nom_fichier)
    with open(chemin_complet, "w", encoding="utf-8") as f:
      f.write(generer_html_individuel(donneur, receveurs, tous_membres))
    liens_generes[donneur] = f"{URL_GITHUB}/{nom_fichier}"

  # Alerts (on quantities, without showing targets)
  comptes = {d: len(r) for d, r in attributions.items()}
  min_c = min(comptes.values())
  max_c = max(comptes.values())
  alertes = []
  for d, nb in comptes.items():
    if nb == 0:
      alertes.append(f"⚠️ {d} n'a aucun receveur (pas assez de participants).")
    elif nb == 1:
      alertes.append(
          f"⚠️ {d} n'a pioché qu'un seul receveur (pas assez de participants)."
      )
    elif min_c != max_c and nb > min_c:
      alertes.append(
          f"ℹ️ {d} a eu plus de receveurs que les autres ({nb} au lieu de"
          f" {min_c})."
      )
  for d, evites in A_EVITER.items():
    if any(r in evites for r in attributions[d]):
      alertes.append(
          f"ℹ️ {d} a dû tirer une personne qu'il/elle préférait éviter."
      )
  texte_alerte = (
      "\n".join(alertes)
      if alertes
      else f"✅ Distribution équilibrée ({min_c} receveur(s) par adulte donneur)."
  )

  ouvrir_tableau_de_bord(liens_generes, attributions, tous_membres, texte_alerte)
  for nom, lien in liens_generes.items():
    print(f"{nom} : {lien}")  # au cas où le navigateur ne s'ouvre pas


if __name__ == "__main__":
  main()
