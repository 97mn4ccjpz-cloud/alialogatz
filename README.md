# PS5 Alert France — première version

Bot expérimental **achats en ligne uniquement**. Ne scanne pas les stocks physiques. Vérifie uniquement les produits et distributeurs décrits dans `products.json` (Boulanger, Cultura, Auchan). Ne surveille **pas encore** Fnac, Darty, Carrefour, etc. : pas de support fiable mis en place pour leurs pages.

## Prérequis
- Un compte GitHub gratuit ; dépôt **public** pour l'exécution GitHub Actions gratuite sur les runners standards (les fichiers et résultats d'exécution seront publics).
- Un bot Telegram déjà créé avec BotFather, puis `/start` envoyé dans le chat du bot.
- Aucun moyen de paiement requis. N'enregistre pas de carte sur GitHub.

## Sur iPhone
1. Crée un dépôt GitHub **public** vide, exemple `ps5-alerte-fr`.
2. Depuis Safari, ouvre le dépôt puis `Add file` > `Upload files`. Décompresse l'archive dans l'app Fichiers et envoie `tracker.py`, `products.json`, `requirements.txt`, `README.md`. Pour le fichier caché `.github/workflows/ps5.yml`, crée les dossiers dans l'interface GitHub via `Add file > Create new file` puis colle son contenu (GitHub autorise le chemin complet `.github/workflows/ps5.yml`).
3. Dans Settings > Secrets and variables > Actions > New repository secret, crée `TELEGRAM_BOT_TOKEN` avec le token de BotFather. **Ne mets jamais ce token dans un fichier public ou un message.**
4. Pour trouver ton `TELEGRAM_CHAT_ID`, ouvre la conversation de ton bot et utilise sur Safari `https://api.telegram.org/bot<TON_TOKEN>/getUpdates`, en remplaçant `<TON_TOKEN>` par le token uniquement dans la barre d'adresse **sur ton propre iPhone**. Cherche `"chat":{"id":123...}`. Ne partage pas cette URL ni une capture contenant le token. Si la liste est vide, renvoie un message à ton bot puis recharge. Mets l'ID dans un second secret `TELEGRAM_CHAT_ID`.
5. Dans `Actions` > `PS5 — veille en ligne` > `Run workflow` pour tester. Ouvre les logs de l'exécution. S'il est indiqué `unknown`, le site ne permet pas de vérifier la disponibilité : le bot **n'alerte pas** plutôt que d'inventer.
6. Les exécutions programmées arrivent environ toutes les 15 minutes (GitHub peut en retarder ou ignorer). Pour arrêter, onglet Actions > workflow > menu `...` > `Disable workflow`.

## Garanties et limites
- Pas d'achat automatique, aucune facturation à l'alerte. Des limites GitHub et des règles propres aux sites s'appliquent.
- Le script ne suit pas les marketplaces et ne déclenche pas d'alerte si le vendeur direct n'est pas identifiable.
- Une page peut être bloquée ou son HTML peut changer ; certains produits resteront `unknown`. La disponibilité géographique en France n'est pas vérifiée par code postal, et la disponibilité peut disparaître entre l'alerte et l'achat.
- Les pages Auchan qui demandent de choisir un magasin sont traitées comme non disponibles pour l'achat en ligne.
- Les exécutions GitHub Actions ne sont pas parfaitement ponctuelles. Dans un dépôt public, les workflows planifiés peuvent être désactivés après 60 jours d'inactivité.
- Les seuils et extracteurs sont conservateurs pour éviter les faux positifs ; une vraie offre peut être manquée.

## Arrêter au bout d'un mois
Dans GitHub : Actions > `PS5 — veille en ligne` > menu `...` > `Disable workflow`. Aucun abonnement à résilier si tu n'as enregistré aucun moyen de paiement.
