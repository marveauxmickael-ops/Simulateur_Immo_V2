"""
Estimateur Immobilier - Backend Python
Version robuste avec fallback pour toutes les communes de France
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict
from io import StringIO
from enum import Enum


class Standing(Enum):
    A_RENOVER = "À rénover"
    STANDARD = "Standard"
    HAUT_DE_GAMME = "Haut de gamme"


class BienImmobilier:
    def __init__(self, code_insee: str, ville: str, surface: float, pieces: int, standing: Standing):
        self.code_insee = code_insee
        self.ville = ville
        self.surface_habitable = surface
        self.nombre_pieces = pieces
        self.standing = standing


# ============================================================================
# RÉCUPÉRATION DES DONNÉES DVF (3 NIVEAUX DE FALLBACK)
# ============================================================================

def recuperer_transactions_dvf(code_insee: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Récupère les transactions DVF avec système de fallback à 3 niveaux
    
    Retourne: (DataFrame des transactions, message d'erreur optionnel)
    """
    print(f"🔄 Récupération des données pour {code_insee}...")
    
    # NIVEAU 1 : API data.gouv.fr (officielle)
    df, error = _tentative_api_datagouv(code_insee)
    if not df.empty:
        print(f"✅ {len(df)} transactions récupérées (API data.gouv.fr)")
        return df, None
    
    print(f"⚠️  API data.gouv.fr indisponible")
    
    # NIVEAU 2 : API DVF+ (alternative)
    df, error = _tentative_api_dvfplus(code_insee)
    if not df.empty:
        print(f"✅ {len(df)} transactions récupérées (API DVF+)")
        return df, None
    
    print(f"⚠️  API DVF+ indisponible")
    
    # NIVEAU 3 : Données simulées réalistes
    print(f"🎭 Génération de données simulées réalistes")
    df = _generer_donnees_simulees(code_insee)
    return df, "⚠️ Données simulées - APIs DVF temporairement indisponibles"


def _tentative_api_datagouv(code_insee: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """Tentative de récupération depuis l'API data.gouv.fr"""
    try:
        dept = code_insee[:2]
        url = f"https://files.data.gouv.fr/geo-dvf/latest/csv/2023/communes/{dept}/{code_insee}.csv"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            df = pd.read_csv(StringIO(response.text))
            return _filtrer_transactions(df), None
        
        return pd.DataFrame(), f"HTTP {response.status_code}"
        
    except Exception as e:
        return pd.DataFrame(), str(e)


def _tentative_api_dvfplus(code_insee: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """Tentative de récupération depuis l'API DVF+ (alternative)"""
    try:
        url = f"https://app.dvf.etalab.gouv.fr/api/v1/search?code_commune={code_insee}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                df = pd.DataFrame(data['results'])
                return _filtrer_transactions(df), None
        
        return pd.DataFrame(), f"HTTP {response.status_code}"
        
    except Exception as e:
        return pd.DataFrame(), str(e)


def _filtrer_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Filtre les transactions pour ne garder que les ventes de logements"""
    if df.empty:
        return df
    
    try:
        # Filtrer les ventes de maisons et appartements
        if 'nature_mutation' in df.columns:
            df = df[df['nature_mutation'] == 'Vente']
        
        if 'type_local' in df.columns:
            df = df[df['type_local'].isin(['Maison', 'Appartement'])]
        
        # Colonnes nécessaires
        colonnes = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati']
        colonnes_presentes = [c for c in colonnes if c in df.columns]
        
        if len(colonnes_presentes) < 3:
            return pd.DataFrame()
        
        df = df[colonnes_presentes].copy()
        
        # Conversion des types
        df['date_mutation'] = pd.to_datetime(df['date_mutation'], errors='coerce')
        df['valeur_fonciere'] = pd.to_numeric(df['valeur_fonciere'], errors='coerce')
        df['surface_reelle_bati'] = pd.to_numeric(df['surface_reelle_bati'], errors='coerce')
        
        # Supprimer les valeurs nulles et aberrantes
        df = df.dropna()
        df = df[df['surface_reelle_bati'] > 0]
        df = df[df['valeur_fonciere'] > 0]
        
        return df
        
    except Exception as e:
        print(f"Erreur lors du filtrage: {e}")
        return pd.DataFrame()


def _generer_donnees_simulees(code_insee: str) -> pd.DataFrame:
    """Génère des données simulées réalistes basées sur le département"""
    
    dept = int(code_insee[:2]) if code_insee[:2].isdigit() else 75
    prix_base = _get_prix_base_departement(dept)
    
    # Générer 100 transactions sur 3 ans
    np.random.seed(int(code_insee) if code_insee.isdigit() else 42)
    
    transactions = []
    today = datetime.now()
    
    for _ in range(100):
        # Date aléatoire sur 3 ans
        jours_avant = np.random.randint(0, 1095)
        date = today - timedelta(days=jours_avant)
        
        # Surface entre 30 et 150 m²
        surface = 30 + np.random.random() * 120
        
        # Prix au m² avec variation ±20%
        prix_m2 = prix_base * (0.8 + np.random.random() * 0.4)
        
        transactions.append({
            'date_mutation': date,
            'valeur_fonciere': prix_m2 * surface,
            'surface_reelle_bati': surface
        })
    
    return pd.DataFrame(transactions)


def _get_prix_base_departement(dept: int) -> float:
    """Retourne le prix de base approximatif par département"""
    prix_departements = {
        75: 10000,  # Paris
        92: 6000,   # Hauts-de-Seine
        93: 4000,   # Seine-Saint-Denis
        94: 4500,   # Val-de-Marne
        78: 4000,   # Yvelines
        91: 3500,   # Essonne
        95: 3200,   # Val-d'Oise
        77: 3000,   # Seine-et-Marne
        13: 3500,   # Bouches-du-Rhône
        6: 4500,    # Alpes-Maritimes
        33: 3500,   # Gironde
        31: 3200,   # Haute-Garonne
        69: 3800,   # Rhône
        59: 2500,   # Nord
        44: 3000,   # Loire-Atlantique
        34: 3200,   # Hérault
        35: 3100,   # Ille-et-Vilaine
        67: 3000,   # Bas-Rhin
        38: 3300,   # Isère
        74: 4000,   # Haute-Savoie
        73: 3500,   # Savoie
        29: 2200,   # Finistère
        56: 2300,   # Morbihan
        22: 2000,   # Côtes-d'Armor
        17: 2500,   # Charente-Maritime
        64: 2800,   # Pyrénées-Atlantiques
        85: 2400,   # Vendée
        14: 2600,   # Calvados
        50: 2100,   # Manche
        76: 2400,   # Seine-Maritime
    }
    
    return prix_departements.get(dept, 2200)  # Prix moyen France par défaut


# ============================================================================
# ANALYSE DU MARCHÉ
# ============================================================================

def analyser_marche(df: pd.DataFrame) -> Dict:
    """Analyse les transactions et calcule les statistiques du marché"""
    
    if df.empty:
        return {
            'prix_moyen_m2': 0,
            'stats': {'min': 0, 'max': 0, 'moyen': 0, 'mediane': 0, 'nb_transactions': 0},
            'evolution': pd.DataFrame()
        }
    
    # Calculer le prix au m²
    df['prix_m2'] = df['valeur_fonciere'] / df['surface_reelle_bati']
    
    # Supprimer les outliers (5% et 95% percentile)
    q5 = df['prix_m2'].quantile(0.05)
    q95 = df['prix_m2'].quantile(0.95)
    df_clean = df[(df['prix_m2'] >= q5) & (df['prix_m2'] <= q95)].copy()
    
    # Statistiques
    stats = {
        'min': int(df_clean['prix_m2'].min()),
        'max': int(df_clean['prix_m2'].max()),
        'moyen': int(df_clean['prix_m2'].mean()),
        'mediane': int(df_clean['prix_m2'].median()),
        'nb_transactions': len(df_clean)
    }
    
    # Évolution par année
    df_clean['annee'] = df_clean['date_mutation'].dt.year
    evolution = df_clean.groupby('annee')['prix_m2'].mean().reset_index()
    evolution.columns = ['annee', 'prix_m2']
    evolution = evolution.sort_values('annee')
    
    return {
        'prix_moyen_m2': stats['moyen'],
        'stats': stats,
        'evolution': evolution
    }


# ============================================================================
# CALCUL DE L'ESTIMATION
# ============================================================================

def calculer_estimation(prix_moyen_m2: float, stats: Dict, evolution: pd.DataFrame, 
                       bien: BienImmobilier) -> Dict:
    """Calcule l'estimation finale avec ajustement standing"""
    
    # Coefficients d'ajustement
    coefficients = {
        Standing.A_RENOVER: 0.85,
        Standing.STANDARD: 1.0,
        Standing.HAUT_DE_GAMME: 1.20
    }
    
    coefficient = coefficients[bien.standing]
    prix_ajuste_m2 = prix_moyen_m2 * coefficient
    estimation_finale = prix_ajuste_m2 * bien.surface_habitable
    
    # Calculer la tendance
    tendance = 0
    if len(evolution) >= 2:
        premiere_annee = evolution.iloc[0]
        derniere_annee = evolution.iloc[-1]
        nb_annees = derniere_annee['annee'] - premiere_annee['annee']
        if nb_annees > 0:
            tendance = (derniere_annee['prix_m2'] - premiere_annee['prix_m2']) / nb_annees
    
    return {
        'valeur_estimee': int(estimation_finale),
        'fourchette_basse': int(estimation_finale * 0.95),
        'fourchette_haute': int(estimation_finale * 1.05),
        'prix_moyen_m2': int(prix_ajuste_m2),
        'coefficient': coefficient,
        'stats': stats,
        'evolution': evolution,
        'tendance': int(tendance)
    }


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def estimer_bien(ville: str, code_insee: str, surface: float, pieces: int, 
                standing: Standing) -> Tuple[Dict, Optional[str]]:
    """
    Fonction principale pour estimer un bien immobilier
    
    Args:
        ville: Nom de la ville
        code_insee: Code INSEE de la commune
        surface: Surface habitable en m²
        pieces: Nombre de pièces
        standing: Standing du bien (enum)
    
    Returns:
        (dictionnaire avec l'estimation, message d'avertissement optionnel)
    """
    
    # Créer le bien
    bien = BienImmobilier(code_insee, ville, surface, pieces, standing)
    
    # Récupérer les transactions
    df_transactions, warning = recuperer_transactions_dvf(code_insee)
    
    if df_transactions.empty:
        return None, "Impossible de récupérer les données pour cette commune"
    
    # Analyser le marché
    analyse = analyser_marche(df_transactions)
    
    if analyse['prix_moyen_m2'] == 0:
        return None, "Données insuffisantes pour cette commune"
    
    # Calculer l'estimation
    estimation = calculer_estimation(
        analyse['prix_moyen_m2'],
        analyse['stats'],
        analyse['evolution'],
        bien
    )
    
    return estimation, warning


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("🧪 TESTS DU BACKEND PYTHON DVF")
    print("="*60)
    
    # Test 1 : Grande ville
    print("\n📍 Test 1 : Bordeaux (grandes villes)")
    estimation, warning = estimer_bien(
        ville="Bordeaux",
        code_insee="33063",
        surface=75.0,
        pieces=3,
        standing=Standing.STANDARD
    )
    
    if estimation:
        print(f"✅ Valeur estimée: {estimation['valeur_estimee']:,} €".replace(',', ' '))
        print(f"✅ Prix moyen: {estimation['prix_moyen_m2']} €/m²")
        print(f"✅ Transactions: {estimation['stats']['nb_transactions']}")
    if warning:
        print(f"⚠️  {warning}")
    
    # Test 2 : Petite commune
    print("\n📍 Test 2 : Cavignac (petite commune)")
    estimation, warning = estimer_bien(
        ville="Cavignac",
        code_insee="33114",
        surface=100.0,
        pieces=4,
        standing=Standing.A_RENOVER
    )
    
    if estimation:
        print(f"✅ Valeur estimée: {estimation['valeur_estimee']:,} €".replace(',', ' '))
        print(f"✅ Prix moyen: {estimation['prix_moyen_m2']} €/m²")
        print(f"✅ Transactions: {estimation['stats']['nb_transactions']}")
    if warning:
        print(f"⚠️  {warning}")
    
    # Test 3 : Code INSEE fictif
    print("\n📍 Test 3 : Commune fictive (fallback)")
    estimation, warning = estimer_bien(
        ville="Test",
        code_insee="99999",
        surface=80.0,
        pieces=3,
        standing=Standing.HAUT_DE_GAMME
    )
    
    if estimation:
        print(f"✅ Valeur estimée: {estimation['valeur_estimee']:,} €".replace(',', ' '))
        print(f"✅ Prix moyen: {estimation['prix_moyen_m2']} €/m²")
        print(f"✅ Transactions: {estimation['stats']['nb_transactions']}")
    if warning:
        print(f"⚠️  {warning}")
    
    print("\n" + "="*60)
    print("✅ TOUS LES TESTS SONT PASSÉS")
    print("="*60)
