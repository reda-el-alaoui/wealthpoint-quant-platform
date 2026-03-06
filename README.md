# ◈ WealthPoint — Analytics Platform

> Plateforme d'analyse quantitative de portefeuille · Position-based · Wealth Management

---

## Sommaire

1. [Vue d'ensemble](#vue-densemble)
2. [Modules](#modules)
3. [Installation](#installation)
4. [Structure des fichiers](#structure-des-fichiers)
5. [Authentification & Login](#authentification--login)
6. [Configuration Streamlit](#configuration-streamlit)
7. [Dépendances](#dépendances)
8. [Lancement](#lancement)
9. [Notes techniques](#notes-techniques)
10. [Limites & Disclaimer](#limites--disclaimer)

---

## Vue d'ensemble

WealthPoint est une plateforme d'analyse quantitative de portefeuille **position-based** : elle fonctionne à partir d'un **snapshot des positions actuelles** (tickers, poids, devises, caractéristiques financières), sans nécessiter l'historique transactionnel complet du client.

Ce paradigme est adapté aux **family offices**, **banques privées** et **conseillers en gestion de patrimoine**, où les actifs sont dispersés entre plusieurs dépositaires et où la consolidation des données est coûteuse ou incomplète.

La plateforme couvre à la fois l'**actif** (risque, projection, stress) et le **passif** (dette, amortissement) du bilan client.

---

## Modules

| # | Module | Horizon | Paradigme | Description |
|---|--------|---------|-----------|-------------|
| 01 | **Risk Analytics** | Court terme (1–20J) | Statistique / paramétrique | VaR, CVaR, Monte Carlo Student-t, GARCH(1,1), corrélations de crise |
| 02 | **Wealth Forecast** | Long terme (10–50 ans) | Monte Carlo stochastique | Projection patrimoniale, événements de vie, fan chart P10/P50/P90 |
| 03 | **Stress Tests** | Événementiel | Historique / factoriel | 9 scénarios, duration repricing, FX, facteurs, bootstrap P10/P90 |
| 04 | **Debt Engine** | Contractuel (1–30 ans) | Annuité + Vasicek | Amortisation fixe/variable/IO, caps/floors, 9 tests mathématiques |

### Module 01 — Risk Analytics

Mesure le risque courant du portefeuille à partir des positions actuelles.

- **VaR paramétrique** (95%, 99%) avec distribution gaussienne et Student-t
- **CVaR / Expected Shortfall** — mesure cohérente (Artzner et al. 1999)
- **Monte Carlo** — 10 000 simulations avec queues épaisses (Student-t, ν=5)
- **GARCH(1,1)** — modélisation du clustering de volatilité (Bollerslev 1986)
- **Matrice de corrélation** — régime normal vs régime de crise (seuil −1.5σ)
- **7 stress scénarios** intégrés (GFC, COVID, Rates Shock, etc.)

### Module 02 — Wealth Forecast

Projette la trajectoire patrimoniale sur des horizons de 10 à 50 ans.

- **Monte Carlo** — dynamique `W(t+1) = W(t)·(1+R(t)) + CF(t)`, 1 000 trajectoires
- **4 classes d'actif** — Actions, Obligations, Alternatives, Private Equity
- **Événements de vie** — apports, retraits, héritages à des dates spécifiées
- **Correction inflation** — projections nominales ou réelles
- **Fan chart** — bandes P10 / P25 / P50 / P75 / P90

### Module 03 — Stress Tests V2

Simule l'impact de crises historiques ou hypothétiques sur le portefeuille.

**9 scénarios** :

| Scénario | Période | Type |
|----------|---------|------|
| Dot-com Bust | 2000–2002 | Historique |
| 9/11 Shock | Sep 2001 | Historique |
| GFC / Lehman | 2007–2009 | Historique |
| COVID Crash | Fév–Mar 2020 | Historique |
| Rates Shock 2022 | Jan–Oct 2022 | Historique |
| Taper Tantrum | Mai–Jun 2013 | Historique |
| EU Sovereign Debt | 2010–2011 | Historique |
| Crypto Winter | Nov 2021–Déc 2022 | Historique |
| Inflation Persistante | — | Custom / forward-looking |

**9 enhancements V2** :

1. Proxy substitution chain avec scoring de confiance
2. Score de confiance global par scénario
3. Duration-based bond repricing (`ΔP ≈ −D·Δr − D_spread·Δspread`)
4. FX decomposition (EUR, GBP, JPY, CHF)
5. Diversification haircut (peak-to-trough, configurable 0–40%)
6. Bootstrap confidence bands P10/P90 (block bootstrap, 300 itérations)
7. 3 scénarios supplémentaires vs V1
8. Factor-based repricing (6 facteurs : market, size, value, EM, commodities, gold)
9. Private asset haircuts (PE +15%, RE +10%)

### Module 04 — Debt Cashflow Engine

Modélise le passif du client : amortissement des prêts immobiliers et professionnels.

**4 portefeuilles préconfigurés** :

| Portefeuille | Notional | Prêts | Caractéristiques |
|---|---|---|---|
| 🏠 Résidentiel Classique | €1.015M | 3 | Fixe + variable, 15–25A |
| 🏢 Investisseurs Locatifs | €1.217M | 4 | SCI variable, IO 60M, path BEAR |
| 🏗️ Patrimonial HNW | €6.34M | 5 | IO 36–60M, prêts jusqu'à €2.4M |
| 🌱 Primo-Accédants PTZ | €403k | 3 | PTZ 0%, crédit conso variable |

**Fonctionnalités** :
- Taux fixe, variable (reset 1/3/6/12M), Interest-Only
- Lifetime cap, periodic cap, floor contractuel
- Trajectoires Vasicek : BASE / BEAR (+150 bps, cap 9%) / BULL (−100 bps, floor 0.5%)
- **Fix critique** : `n_remaining = loan.term_months − t` (pas `horizon − t`)
- 9 tests unitaires automatisés (suite de vérification de production)
- Builder de prêt custom dans la sidebar

---

## Installation

### Prérequis

- Python **3.9+**
- pip

### Étapes

```bash
# 1. Cloner le dépôt
git clone <repo-url>
cd wealthpoint_platform

# 2. Créer un environnement virtuel (recommandé)
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. (Optionnel) Configurer les credentials de login
mkdir -p .streamlit
cat > .streamlit/secrets.toml << 'EOF'
[users]
demo    = "wealthpoint2026"
admin   = "wp-admin-2026"
analyst = "quant#2026"
EOF

# 5. Lancer
streamlit run Home.py
```

---

## Structure des fichiers

```
wealthpoint_platform/
│
├── Home.py                        # Landing page (point d'entrée Streamlit)
├── Login.py                       # Page d'authentification standalone
├── wealthpoint_theme.py           # Design system partagé (couleurs, CSS, helpers)
├── requirements.txt               # Dépendances Python
├── README.md                      # Ce fichier
│
├── .streamlit/
│   ├── config.toml                # Thème clair forcé (fond blanc)
│   └── secrets.toml               # Credentials (NE PAS committer — dans .gitignore)
│
└── pages/
    ├── 1_Risk_Analytics.py        # Module 01 — VaR, CVaR, Monte Carlo, GARCH
    ├── 2_Wealth_Forecast.py       # Module 02 — Projection patrimoniale
    ├── 3_Stress_Tests.py          # Module 03 — 9 scénarios historiques V2
    └── 4_Debt_Engine.py           # Module 04 — Amortisation, Vasicek, IO
```

---

## Authentification & Login

### Vue d'ensemble

La page `Login.py` est un point d'entrée **standalone** qui protège l'accès à la plateforme. Elle peut être activée comme page principale en la renommant `Home.py`.

### Activation en 2 étapes

```bash
# 1. Sauvegarder la landing page actuelle
mv Home.py Home_app.py

# 2. Activer la page login comme point d'entrée
cp Login.py Home.py
```

Après login réussi, `Home.py` importe automatiquement `Home_app` pour afficher la plateforme.

### Configuration des credentials

Créer `.streamlit/secrets.toml` :

```toml
[users]
demo    = "wealthpoint2026"
admin   = "wp-admin-2026"
analyst = "quant#2026"
```

> ⚠️ **Ne jamais committer `secrets.toml`** :

```bash
echo ".streamlit/secrets.toml" >> .gitignore
```

### Credentials par défaut (fallback démo)

Si `secrets.toml` est absent, ces credentials de fallback sont utilisés automatiquement :

| Utilisateur | Mot de passe | Rôle |
|-------------|--------------|------|
| `demo` | `wealthpoint2026` | Lecture |
| `admin` | `wp-admin-2026` | Admin |
| `analyst` | `quant#2026` | Analyste |

### Mécanique de sécurité

- **Rate limiting** : 5 tentatives max avant verrouillage de session
- **Session state** : `wp_authenticated` + `wp_user` stockés côté Streamlit
- **Pas de persistence** : la session expire à la fermeture du navigateur

---

## Configuration Streamlit

### `.streamlit/config.toml`

```toml
[theme]
base                     = "light"
backgroundColor          = "#FFFFFF"
secondaryBackgroundColor = "#F7F3EE"
textColor                = "#1A1A1A"
primaryColor             = "#B19069"
font                     = "sans serif"

[server]
headless = true
```

Ce fichier force le thème clair indépendamment du mode sombre du système.

---

## Dépendances

```
streamlit>=1.35.0
yfinance>=0.2.40
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.11.0
matplotlib>=3.7.0
seaborn>=0.12.0
```

Bibliothèque standard utilisée (pas d'installation nécessaire) : `dataclasses`, `warnings`, `copy`, `sys`, `os`, `time`, `datetime`.

---

## Lancement

### Développement local

```bash
streamlit run Home.py
# → http://localhost:8501
```

### Options utiles

```bash
# Port personnalisé
streamlit run Home.py --server.port 8502

# Mode headless (serveur sans ouverture navigateur)
streamlit run Home.py --server.headless true

# Désactiver le watcher (production)
streamlit run Home.py --server.fileWatcherType none
```

### Docker (exemple minimal)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY ../../Downloads/wealthpoint_platform%204/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../../Downloads/wealthpoint_platform%204 .
EXPOSE 8501

CMD ["streamlit", "run", "Home.py", \
     "--server.headless=true", \
     "--server.port=8501"]
```

---

## Notes techniques

### Architecture position-based

La plateforme ne requiert **aucun historique transactionnel**. Les données de marché (prix historiques) sont téléchargées via `yfinance` au runtime et mises en cache :

```python
@st.cache_data(show_spinner=False)
def _prices(tickers_key: tuple) -> pd.DataFrame:
    return yf.download(list(tickers_key), ...)
```

### Design system (`wealthpoint_theme.py`)

Partagé entre tous les modules :

| Élément | Valeur |
|---------|--------|
| `PRIMARY` | `#B19069` (or chaud) |
| `PRIMARY_DARK` | `#8C7050` |
| Titre | Cormorant Garamond, weight 300 |
| Corps | DM Sans, weight 400 |
| Helpers | `kpi_card()`, `page_header()`, `section()`, `sidebar_brand()` |

Chaque module a sa couleur d'accent propre :

| Module | Accent |
|--------|--------|
| 01 — Risk | `#B19069` (PRIMARY) |
| 02 — Forecast | `#8C7050` (PRIMARY_DARK) |
| 03 — Stress | `#7C3AED` (violet) |
| 04 — Debt | `#0F766E` (teal) |

### Bug fix Debt Engine (critique)

```python
# ✅ Correct — terme total depuis l'origination
n_remaining = loan.term_months - t

# ❌ Incorrect — tronque la durée à l'horizon d'affichage
n_remaining = horizon - t
```

Exemple : Dupont 520k @ 1.9% / 20A, horizon affiché = 10A

| `n` utilisé | Mensualité | Erreur |
|------------|-----------|--------|
| n=240 ✅ | **€2 606** | 0% |
| n=120 ❌ | **€4 761** | +83% |

### Compatibilité yfinance MultiIndex

Le Module 03 gère les deux layouts de MultiIndex :

```python
# yfinance ≥0.2.x : (price_type, ticker)
if "Close" in raw.columns.get_level_values(0):
    out = raw["Close"]
# yfinance <0.2.x : (ticker, price_type)
else:
    out = raw.xs("Close", axis=1, level=1)
```

---

## Limites & Disclaimer

### Limites générales

- **Données yfinance** : qualité variable ; certains tickers peuvent manquer de données avant 2003–2006
- **Poids constants** : allocation fixe sur toute la période (pas de rebalancement modélisé)
- **Liquidité parfaite** : coûts de transaction et market impact non modélisés
- **Actifs non cotés** : PE et immobilier utilisent des proxies ETF (IWM, VNQ) avec haircuts

### Limites par module

| Module | Limite principale |
|--------|-------------------|
| 01 — Risk | VaR ne capte pas les événements sans précédent historique |
| 02 — Forecast | Rendements i.i.d. ; sequence-of-returns risk ignoré |
| 03 — Stress | Trajectoire de taux unique par scénario ; pas de corrélation dynamique |
| 04 — Debt | Pas de prépaiement, pas d'ADE ; convention 30/360 vs Actual/365 |

### Disclaimer

> Les résultats produits par WealthPoint sont des **estimations indicatives** à des fins illustratives et pédagogiques. Ils ne constituent pas un conseil en investissement, un conseil en crédit ou une recommandation financière. Les performances passées ne préjugent pas des performances futures.
>
> **Usage interne uniquement — pas un conseil en investissement.**

---

*2026 · WealthPoint Analytics Platform · Ingénierie Quantitative*
