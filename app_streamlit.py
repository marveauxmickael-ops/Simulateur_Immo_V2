"""
Application Streamlit - Estimateur Immobilier DVF
Version complète avec backend robuste
"""

import streamlit as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from dvf_backend import estimer_bien, Standing

# Configuration de la page
st.set_page_config(
    page_title="Estimateur Immobilier DVF",
    page_icon="🏡",
    layout="wide"
)

# CSS personnalisé
st.markdown("""
<style>
    .stAlert > div {
        padding: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🏡 Estimateur Immobilier")
st.markdown("*Basé sur les Demandes de Valeurs Foncières (DVF) officielles*")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📝 Paramètres du bien")
    
    ville = st.text_input(
        "Ville",
        value="Bordeaux",
        help="Nom de la ville"
    )
    
    code_insee = st.text_input(
        "Code INSEE",
        value="33063",
        help="Code INSEE de la commune (5 chiffres)"
    )
    
    st.markdown("**💡 Exemples de codes INSEE:**")
    with st.expander("Voir les codes courants"):
        st.markdown("""
        - **Paris**: 75056
        - **Marseille**: 13055
        - **Lyon**: 69123
        - **Toulouse**: 31555
        - **Bordeaux**: 33063
        - **Lille**: 59350
        - **Nantes**: 44109
        
        [🔍 Rechercher un code INSEE](https://www.insee.fr/fr/recherche/recherche-geographique)
        """)
    
    st.markdown("---")
    
    surface = st.number_input(
        "Surface habitable (m²)",
        min_value=10.0,
        max_value=500.0,
        value=75.0,
        step=5.0
    )
    
    pieces = st.number_input(
        "Nombre de pièces",
        min_value=1,
        max_value=20,
        value=3,
        step=1
    )
    
    standing_label = st.selectbox(
        "Standing du bien",
        ["Standard", "À rénover", "Haut de gamme"]
    )
    
    # Mapping vers enum
    standing_map = {
        "Standard": Standing.STANDARD,
        "À rénover": Standing.A_RENOVER,
        "Haut de gamme": Standing.HAUT_DE_GAMME
    }
    standing = standing_map[standing_label]
    
    st.markdown("---")
    
    estimer_button = st.button(
        "💰 Estimer le bien",
        type="primary",
        use_container_width=True
    )

# Zone principale
if estimer_button:
    with st.spinner(f"🔄 Analyse en cours pour {ville}..."):
        
        # Appel du backend
        estimation, warning = estimer_bien(
            ville=ville,
            code_insee=code_insee,
            surface=surface,
            pieces=pieces,
            standing=standing
        )
        
        if estimation is None:
            st.error(f"❌ {warning}")
            st.info("""
            **Suggestions:**
            - Vérifiez que le code INSEE est correct (5 chiffres)
            - Essayez avec une ville plus grande
            - Consultez le site de l'INSEE pour le bon code
            """)
        else:
            # Afficher l'avertissement si données simulées
            if warning:
                st.warning(warning)
                st.info("""
                Les APIs DVF officielles sont temporairement indisponibles. 
                Cette estimation utilise des données simulées réalistes basées 
                sur les prix moyens du département.
                """)
            else:
                st.success(f"✅ {estimation['stats']['nb_transactions']} transactions DVF analysées pour {ville}")
            
            # Affichage des résultats
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📊 Statistiques du marché")
                
                # Métriques en 2 colonnes
                metric_col1, metric_col2 = st.columns(2)
                with metric_col1:
                    st.metric(
                        "Prix minimum",
                        f"{estimation['stats']['min']:,} €/m²".replace(',', ' ')
                    )
                    st.metric(
                        "Prix moyen",
                        f"{estimation['stats']['moyen']:,} €/m²".replace(',', ' ')
                    )
                
                with metric_col2:
                    st.metric(
                        "Prix maximum",
                        f"{estimation['stats']['max']:,} €/m²".replace(',', ' ')
                    )
                    st.metric(
                        "Médiane",
                        f"{estimation['stats']['mediane']:,} €/m²".replace(',', ' ')
                    )
                
                st.info(f"📈 **{estimation['stats']['nb_transactions']}** transactions analysées")
                
                # Tendance
                if estimation['tendance'] != 0:
                    tendance_emoji = "📈" if estimation['tendance'] > 0 else "📉"
                    tendance_text = "hausse" if estimation['tendance'] > 0 else "baisse"
                    st.metric(
                        "Tendance du marché",
                        f"{abs(estimation['tendance'])} €/m²/an",
                        delta=f"{tendance_text}",
                        delta_color="normal" if estimation['tendance'] > 0 else "inverse"
                    )
                
                st.markdown("---")
                
                st.subheader("🏠 Détails du bien")
                st.write(f"**Localisation:** {ville} ({code_insee})")
                st.write(f"**Surface:** {surface} m²")
                st.write(f"**Pièces:** {pieces}")
                st.write(f"**Standing:** {standing_label}")
                st.write(f"**Coefficient appliqué:** {estimation['coefficient']}")
            
            with col2:
                st.subheader("📈 Évolution des prix")
                
                if not estimation['evolution'].empty:
                    # Créer le graphique
                    fig, ax = plt.subplots(figsize=(10, 5))
                    
                    evolution = estimation['evolution']
                    ax.plot(
                        evolution['annee'],
                        evolution['prix_m2'],
                        marker='o',
                        color='#2ecc71',
                        linewidth=2,
                        markersize=8
                    )
                    
                    ax.set_title(
                        "Évolution du prix au m²",
                        fontsize=14,
                        fontweight='bold'
                    )
                    ax.set_xlabel("Année", fontsize=11)
                    ax.set_ylabel("Prix €/m²", fontsize=11)
                    ax.grid(True, linestyle='--', alpha=0.3)
                    
                    # Ligne de tendance si suffisamment de données
                    if len(evolution) > 1:
                        import numpy as np
                        z = np.polyfit(evolution['annee'], evolution['prix_m2'], 1)
                        p = np.poly1d(z)
                        ax.plot(
                            evolution['annee'],
                            p(evolution['annee']),
                            "r--",
                            alpha=0.5,
                            label=f"Tendance: {'+' if z[0]>0 else ''}{int(z[0])}€/an"
                        )
                        ax.legend()
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close()
                else:
                    st.info("Pas assez de données pour afficher l'évolution")
            
            # Résultat final
            st.markdown("---")
            st.markdown("## 💰 RÉSULTAT DE L'ESTIMATION")
            
            result_col1, result_col2, result_col3 = st.columns(3)
            
            with result_col1:
                st.metric(
                    "Fourchette basse (-5%)",
                    f"{estimation['fourchette_basse']:,} €".replace(',', ' ')
                )
            
            with result_col2:
                st.metric(
                    "🏠 VALEUR ESTIMÉE",
                    f"{estimation['valeur_estimee']:,} €".replace(',', ' ')
                )
            
            with result_col3:
                st.metric(
                    "Fourchette haute (+5%)",
                    f"{estimation['fourchette_haute']:,} €".replace(',', ' ')
                )
            
            # Informations complémentaires
            with st.expander("🔍 Détails techniques"):
                st.write(f"**Prix moyen secteur (brut):** {estimation['stats']['moyen']:,} €/m²".replace(',', ' '))
                st.write(f"**Prix ajusté (avec standing):** {estimation['prix_moyen_m2']:,} €/m²".replace(',', ' '))
                st.write(f"**Surface du bien:** {surface} m²")
                st.write(f"**Formule:** Prix ajusté × Surface = {estimation['prix_moyen_m2']:,} × {surface} = {estimation['valeur_estimee']:,} €".replace(',', ' '))
                st.write(f"**Source des données:** {'Données simulées' if warning else 'API DVF officielle'}")
            
            # Note finale
            st.success("""
            ✅ **Note importante**
            
            Cette estimation est indicative et ne constitue pas un avis de valeur professionnel.
            Elle est basée sur l'analyse des transactions immobilières récentes dans la commune.
            """)

else:
    # Message d'accueil
    st.info("👈 Configurez les paramètres dans la barre latérale et cliquez sur **Estimer le bien**")
    
    # Guide d'utilisation
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 Comment utiliser cet outil ?
        
        1. **Saisissez** le code INSEE de la commune
        2. **Renseignez** les caractéristiques du bien
        3. **Choisissez** le standing du bien
        4. **Cliquez** sur "Estimer le bien"
        5. **Consultez** les résultats et le graphique
        
        ### 🔍 Trouver un code INSEE
        
        Rendez-vous sur le [site de l'INSEE](https://www.insee.fr/fr/recherche/recherche-geographique)
        pour rechercher le code de votre commune.
        """)
    
    with col2:
        st.markdown("""
        ### 📌 À propos des données
        
        - ✅ Système **robuste** avec 3 niveaux de fallback
        - ✅ Fonctionne pour **toutes les communes**
        - ✅ Données **réelles** quand disponibles (DVF)
        - ✅ Données **simulées réalistes** en fallback
        - ✅ 30+ départements avec prix spécifiques
        
        ### 💡 Coefficients de standing
        
        - **À rénover:** -15% (coefficient 0.85)
        - **Standard:** Prix de base (coefficient 1.0)
        - **Haut de gamme:** +20% (coefficient 1.20)
        """)
    
    st.markdown("---")
    
    # Exemples de communes
    st.subheader("📍 Exemples de communes à tester")
    
    exemple_col1, exemple_col2, exemple_col3 = st.columns(3)
    
    with exemple_col1:
        st.markdown("""
        **Grandes villes**
        - Paris: 75056
        - Lyon: 69123
        - Marseille: 13055
        """)
    
    with exemple_col2:
        st.markdown("""
        **Villes moyennes**
        - Bordeaux: 33063
        - Nantes: 44109
        - Toulouse: 31555
        """)
    
    with exemple_col3:
        st.markdown("""
        **Petites communes**
        - Cavignac: 33114
        - N'importe quel code
        - Fallback automatique
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem 0;'>
    <p>Données fournies par <a href='https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/' target='_blank'>data.gouv.fr</a></p>
    <p>Les estimations sont indicatives et ne constituent pas un avis de valeur professionnel.</p>
    <p style='margin-top: 1rem;'>
        <span style='display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #2ecc71; margin-right: 5px;'></span>
        <span>Système opérationnel pour toutes les communes de France</span>
    </p>
</div>
""", unsafe_allow_html=True)
