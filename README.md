# Vidéos satisfaisantes → TikTok, tous les jours (Docker)

Le conteneur génère chaque jour une vidéo satisfaisante aléatoire (1080×1920, 60 i/s, sons
synthétisés donc sans droits d'auteur) et l'envoie sur TikTok à l'heure choisie.

## Types de vidéos (variable `SCENES`)
| Type | Description |
|---|---|
| `EscapeRings` | 1 à 3 balles prisonnières d'anneaux qui tournent, chacun avec une seule sortie |
| `InfiniteCube` | **Boucle infinie** : une boîte tombe dans une boîte, on plonge dedans... sans fin |
| `InfiniteSpiral` | **Boucle infinie** : spirale hypnotique (illusion « fixe le centre puis regarde ta main ») |
| `GrowingBall` | La balle grandit à chaque rebond jusqu'à remplir le cercle |
| `Multiply` | Les balles se multiplient jusqu'à 1000 |
| `EscapeBox` | Une boîte tourne et s'ouvre, chaque bille qui sort en fait naître d'autres : « 2000 billes en 30 s ? » |
| `RingCountdown` | Une balle brise un à un des dizaines d'anneaux arc-en-ciel, compte à rebours au centre |
| `Katana` | Un sabre tourne, chaque coupe divise une balle en deux : « combien de morceaux ? » |
| `ClockSweep` | Deux aiguilles d'horloge brassent des billes qui se multiplient : « tu dis combien ? » |
| `GearArcs` | Un engrenage et deux arcs en C dédoublent la balle à chaque coup : « 1 balle → 250 ? » |
| `PinArt` | **Boucle infinie** : une plaque 3D en pixels change de forme sans fin |
| `PotatoMerge` | Des patates fusionnent en patates plus grosses (8 personnages tirés parmi plus de 50), une voix de plus en plus grave annonce chaque nouvelle |
| `SongBounce` | Une bille creuse son chemin et rebondit pile sur chaque note d'une musique connue (domaine public, arrangée synthé + basse + batterie) ; le nom se dévoile en cours de route |
| `SongRing` | « Devine la musique » : la musique n'avance que quand une bille touche l'anneau, le jeton x2 multiplie les billes et le morceau finit par jouer en entier |
| `MarbleMelody` | Une bille rebondit de tube en tube et joue des mélodies connues (libres de droits) : « Top 6 des mélodies » |
| `PotatoRace` | Course de 3-4 patates dans des anneaux qui tournent : « quelle patate sort en premier ? » |
| `PotatoSplit` | Une patate géante se divise à chaque rebond, chaque génération révèle de nouveaux personnages |
| `PotatoEscape` | Une patate (ou un duel de deux patates) doit sortir de formes emboîtées |
| `PotatoDuel` | Deux équipes de patates fusionnent côte à côte : la première à faire une patate géante gagne |
| `PlanetMerge` | Fusion de planètes (astéroïde → Lune → … → Soleil), voix de plus en plus grave |
| `SlimeMerge` | Fusion de slimes colorés jusqu'au roi des slimes |
| `SplitBalls` | Une balle se divise à chaque rebond dans une forme qui tourne : « 1 balle → 512 ? » |
| `ShapeEscape` | Formes emboîtées qui tournent, chacune avec une sortie. Solo ou duel Rouge contre Bleu |
| `ParticleMorph` | **Boucle infinie** : nuage de particules 3D qui devient sphère, cube, cœur, galaxie… |
| `Polyrhythm`, `PendulumWave`, `Galton`, `Sorting` | Polyrythmie, pendules, planche de Galton, son d'un tri |

Les boucles infinies ont une dernière image identique à la première : quand TikTok relance la
vidéo, la coupure est invisible et on attend une fin qui n'arrive jamais.

## Centre de contrôle (site web)
Un petit site, `panel`, tourne à côté du robot. On peut y :
- mettre en pause ou relancer la publication, choisir les heures et le nombre de vidéos par jour ;
- cocher les types de vidéos (par exemple uniquement les patates) ;
- régler les proportions de durées (courte, moyenne, normale, longue) ;
- **générer et envoyer une vidéo tout de suite**, puis copier sa légende ;
- revoir les dernières vidéos, copier leur légende ou envoyer celles qui ne l'ont pas été.

Les changements s'appliquent sans redémarrage. Pour l'ouvrir depuis le téléphone via Tailscale,
mets l'IP Tailscale du VPS (`tailscale ip -4`) dans `PANEL_BIND` du `.env`, lance
`docker compose up -d panel`, puis ouvre `http://IP-TAILSCALE:8090` sur le téléphone.

## Durée des vidéos
Chaque jour, une durée est tirée au hasard : **court** (18–28 s), **moyen** (30–42 s),
**normal** (45–58 s) ou **long** (62–72 s). Si aucune vidéo de plus de 61 s n'est sortie
dans les 6 derniers jours, la vidéo du jour est forcément longue : il y en a donc au moins
une par semaine. Chaque type adapte son rythme à la durée demandée.
`python generate.py --length long` impose une durée.

## 1. Créer l'app TikTok (une seule fois)
1. Va sur https://developers.tiktok.com, puis **Manage apps → Connect an app**. Plateforme : **Desktop**.
2. Ajoute les produits **Login Kit** et **Content Posting API**.
   Pour la publication directe, active aussi **Direct Post** dans Content Posting API.
3. Dans Login Kit, ajoute l'URI de redirection `http://localhost:8082/callback`
4. Coche les scopes `user.info.basic` et `video.upload` (et `video.publish` pour la publication directe).
5. Passe l'app en **Sandbox** et ajoute ton compte TikTok dans *Target users*.
6. Note le **Client key** et le **Client secret**.

## Le mini-site demandé par TikTok (sur le VPS)
1. Fais pointer un domaine vers l'IP du VPS (enregistrement DNS A). Si tu n'as pas de domaine,
   un sous-domaine gratuit sur duckdns.org suffit.
2. Ouvre les ports 80 et 443, puis mets `DOMAIN=ton-domaine` dans `.env`.
3. Lance `docker compose --profile site up -d`.
4. Le site est en ligne en https (certificat automatique) :
   `https://ton-domaine/`, `/terms.html` et `/privacy.html`.
5. Pour la vérification TikTok, dépose le fichier `tiktokXXXX.txt` dans `site/` : il est servi immédiatement.

## 2. Déployer sur le VPS
```bash
# copier ce dossier sur le VPS (depuis ton PC)
scp -r tiktok/ user@ton-vps:~/tiktok
ssh user@ton-vps
cd ~/tiktok
cp .env.example .env && nano .env          # colle client key / secret, choisis l'heure
docker compose build
docker compose run --rm tiktok python tiktok.py auth --manual
docker compose up -d
docker compose logs -f                     # affiche « Prochaine vidéo : ... »
```
Pour `auth --manual` :
1. Ouvre le lien affiché sur ton PC ou ton téléphone et accepte.
2. Le navigateur tombe sur une page d'erreur « localhost » : c'est normal.
3. Copie l'adresse de cette page et colle-la dans le terminal.

Le jeton est enregistré dans `data/tokens.json` et se renouvelle tout seul pendant un an.

**Tester tout de suite** : mets `RUN_ON_START=1` dans `.env`, puis lance `docker compose up -d`.

## Brouillon ou publication automatique (`TIKTOK_MODE`)
- `draft` (par défaut) : la vidéo arrive dans les notifications de l'app TikTok. Tu colles la
  légende (fichier `.txt` à côté de la vidéo) et tu publies. Ça marche tout de suite.
- `direct` : publication 100 % automatique avec légende et hashtags. **Mais tant que TikTok n'a
  pas audité ton app, les vidéos postées sont privées** (et ton compte doit être privé). Pour les
  rendre publiques, demande l'audit depuis la page de ton app (le délai dépend de TikTok).
  Ensuite, passe `TIKTOK_MODE=direct`, refais `tiktok.py auth --manual` (pour ajouter le scope
  `video.publish`) et redémarre le conteneur.

## Commandes utiles
```bash
docker compose run --rm tiktok python generate.py --type InfiniteCube   # générer une vidéo précise
docker compose run --rm tiktok python generate.py --list                # liste des types
docker compose run --rm tiktok python daily.py 1                        # générer + envoyer maintenant
docker compose restart                                                  # après une modif du .env
```
Les vidéos se trouvent dans `data/output/`. Celles déjà envoyées sont supprimées après `KEEP_DAYS` jours.

## Sur Windows, sans Docker
`pip install -r requirements.txt`, puis `python generate.py`, `python tiktok.py auth` et
`python daily.py` (les identifiants vont dans `config.json`).

## Ne pas partager
`.env`, `config.json` et `data/tokens.json` donnent accès à ton compte TikTok.
# satisfying
