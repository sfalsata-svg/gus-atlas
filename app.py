import streamlit as st
import pandas as pd
import pickle
import time
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Gus:Atlas", page_icon="🍽️")

# --- CHARGEMENT DU CERVEAU (CACHE) ---
@st.cache_data
def load_brain():
    # On charge le fichier pickle qui contient le DataFrame avec les vecteurs
    with open('gus_brain.pkl', 'rb') as f:
        df = pickle.load(f)
    return df

try:
    df_ingredients = load_brain()
except Exception as e:
    st.error(f"Erreur : Impossible de charger le cerveau de Gus. Vérifiez que 'gus_brain.pkl' est bien présent. {e}")
    st.stop()

# --- MOTEUR DE RECHERCHE INTELLIGENT ---
def find_substitute(ingredient_name, exclude_categories=[]):
    # 1. On cherche l'ingrédient dans la base
    row = df_ingredients[df_ingredients['nom'].str.lower() == ingredient_name.lower()]
    
    if row.empty:
        return None, 0, "Ingrédient inconnu"
    
    target_vector = row['vector'].values[0]
    
    # 2. On calcule la similarité avec tout le monde
    scores = cosine_similarity([target_vector], list(df_ingredients['vector']))[0]
    df_ingredients['score_temp'] = scores
    
    # 3. On trie
    candidates = df_ingredients.sort_values(by='score_temp', ascending=False)
    
    # 4. FILTRE (Exemple simple : on évite l'ingrédient lui-même)
    # Dans une version avancée, ici on filtrerait "Laitier" si l'user est "Vegan"
    # Pour l'instant, on prend juste le meilleur qui n'est pas lui-même
    best_match = candidates[candidates['nom'] != row['nom'].values[0]].iloc[0]
    
    return best_match['nom'], int(best_match['score_temp'] * 100), best_match['desc']

# --- INTERFACE ---

# Styles CSS pour le look "Google"
st.markdown("""
<style>
    .stTextInput input {border-radius: 20px;}
    .big-font {font-size: 20px !important;}
</style>
""", unsafe_allow_html=True)

if 'search_done' not in st.session_state:
    st.session_state.search_done = False
if 'data_result' not in st.session_state:
    st.session_state.data_result = {}

# === PHASE 1 : RECHERCHE ===
if not st.session_state.search_done:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>Gus:Atlas</h1>", unsafe_allow_html=True)
        plat = st.text_input("", placeholder="Ex: Carbonara, Quiche Lorraine...")
        
        # Filtres (Simulés pour l'instant)
        st.write("Vos contraintes :")
        c1, c2, c3, c4 = st.columns(4)
        vegan = c1.checkbox("Vegan")
        sans_lactose = c2.checkbox("Sans Lactose")
        sans_gluten = c3.checkbox("Sans Gluten")
        
        if st.button("Lancer Gus 🚀", use_container_width=True):
            if plat:
                # Simulation d'analyse (Loading)
                bar = st.progress(0)
                status = st.empty()
                for i, txt in enumerate(["Lecture de la recette...", "Détection des allergènes...", "Recherche vectorielle...", "Finalisation..."]):
                    status.text(txt)
                    bar.progress((i+1)*25)
                    time.sleep(0.8)
                
                # --- LOGIQUE INTELLIGENTE ---
                # Pour la démo, on simule une recette de Carbonara si l'user tape "Carbonara"
                # Mais on utilise VRAIMENT ton modèle pour trouver le substitut
                
                ing_problematique = "Crème Fraîche" if sans_lactose or vegan else "Beurre Doux"
                if "carbonara" in plat.lower(): ing_problematique = "Parmesan"
                
                sub_nom, sub_score, sub_desc = find_substitute(ing_problematique)
                
                st.session_state.data_result = {
                    "plat": plat,
                    "bad_ing": ing_problematique,
                    "good_ing": sub_nom,
                    "score": sub_score,
                    "desc": sub_desc
                }
                st.session_state.search_done = True
                st.rerun()

# === PHASE 2 : RÉSULTAT ===
else:
    if st.button("← Retour"):
        st.session_state.search_done = False
        st.rerun()
        
    res = st.session_state.data_result
    
    st.title(f"Résultat pour : {res['plat']}")
    
    col_g, col_d = st.columns([1, 2])
    
    with col_g:
        st.container(border=True)
        st.subheader("💡 Substitution Intelligente")
        st.write(f"Ingrédient détecté : **{res['bad_ing']}**")
        st.markdown(f"### ⬇️ Remplacé par : \n### ✨ {res['good_ing']}")
        st.progress(res['score'])
        st.caption(f"Match : {res['score']}%")
        st.info(f"**Pourquoi ?** {res['desc']}")
        
    with col_d:
        st.subheader("📝 La Recette Adaptée")
        st.warning(f"Cette recette a été modifiée pour utiliser du **{res['good_ing']}**.")
        st.markdown("""
        * 400g de Pâtes
        * 200g de ** Substitut (voir à gauche) **
        * Sel, Poivre
        
        **Instructions :**
        1. Cuire les pâtes.
        2. Mélanger l'ingrédient de substitution avec un peu d'eau de cuisson.
        3. Servir chaud.
        """)
