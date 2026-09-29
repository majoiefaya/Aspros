# ASPROS

**ASPROS** est le noyau d'un assistant personnel connecté. Cette première version fonctionne sans matériel : elle contrôle des appareils simulés, exécute des scènes et interprète des commandes simples en français.

Le projet a été conçu pour pouvoir accueillir plus tard des connecteurs MQTT, Home Assistant, Bluetooth, Matter, Zigbee ou des APIs tierces, sans modifier son moteur de décision.

## Fonctionnalités du MVP

- registre d'appareils et états persistés dans SQLite ;
- appareils simulés : deux lampes, un capteur de température et un ordinateur ;
- commandes en français : allumer, éteindre, régler une luminosité, demander un état ;
- scènes : `mode travail`, `mode nuit`, `tout éteindre` ;
- journal d'audit de toutes les actions ;
- tableau de bord web et API JSON ;
- aucune dépendance Python externe.

## Démarrer

Depuis ce dossier :

```bash
python3 -m aspros.main
```

Ouvre ensuite <http://127.0.0.1:8765>.

Pour choisir un autre port :

```bash
python3 -m aspros.main --port 8080
```

## Exemples de commandes

```text
allume la lampe du bureau
éteins les lampes
règle la lampe du bureau à 40 %
quel est l'état des appareils ?
active le mode travail
mode nuit
```

## API

| Méthode | Route | Rôle |
| --- | --- | --- |
| `GET` | `/api/health` | Vérifie qu'ASPROS est actif |
| `GET` | `/api/devices` | Liste les appareils et leurs états |
| `POST` | `/api/commands` | Interprète une commande texte |
| `POST` | `/api/devices/{id}/actions` | Exécute une action structurée |
| `GET` | `/api/scenes` | Liste les scènes disponibles |
| `POST` | `/api/scenes/{id}/execute` | Exécute une scène |
| `GET` | `/api/audit` | Lit le journal d'activité |

Exemple :

```bash
curl -X POST http://127.0.0.1:8765/api/commands \
  -H 'Content-Type: application/json' \
  -d '{"text":"allume la lampe du bureau"}'
```

## Architecture

```text
aspros/
├── core.py          # Registre, orchestration, scènes et audit
├── commands.py      # Compréhension des commandes textuelles
├── connectors.py    # Contrat de connecteur + simulation
├── storage.py       # Persistance SQLite
├── main.py          # Serveur HTTP et API JSON
└── static/          # Tableau de bord
```

La prochaine étape sera de créer des implémentations de `DeviceConnector` :

- `MqttConnector` pour ESP32 et capteurs ;
- `HomeAssistantConnector` pour les objets connectés existants ;
- `ComputerConnector` pour agir réellement sur le PC avec des autorisations explicites.

## Sécurité à garder lors des futures intégrations

Les actions sensibles (porte, alarme, caméra, paiement, suppression) doivent être classées comme nécessitant une confirmation. Les secrets et jetons d'API ne doivent jamais être placés dans le code source : utilise des variables d'environnement ou un gestionnaire de secrets.
