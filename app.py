import streamlit as st
import pandas as pd
import pickle
import time
import json
from sklearn.metrics.pairwise import cosine_similarity
# On importe OpenAI (maintenant que requirements.txt est à jour)
try:
    from openai import OpenAI
except ImportError:
    st.error("Le module OpenAI n'est pas installé. Vérifiez requirements.txt")
    st.stop()

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Gus:Atlas", page_icon="🍽️")

# --- CSS ---
st.markdown("""
<style>
    .stTextInput input {border-radius: 20px; padding: 10px;}
    .stMultiSelect span {border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DU CERVEAU ---
@st.cache_data
def load_brain():
    try:
        with open('gus_brain.pkl', 'rb') as f:
            return pickle.load(f)
    except:
        return pd.DataFrame() 

df_ingredients = load_brain()

# --- FONCTION GUS (VECTEURS) ---
def get_smart_substitute(ingredient_name):
    if df_ingredients.empty: return None, 0, "DB Missing"
    
    # Recherche basique
    row = df_ingredients[df_ingredients['nom'].str.lower() == ingredient_name.lower()]
    if row.empty: return None, 0, "Inconnu"
    
    target_vector = row['vector'].values[0]
    scores = cosine_similarity([target_vector], list(df_ingredients['vector']))[0]
    df_ingredients['score_temp'] = scores
    
    candidates = df_ingredients.sort_values(by='score_temp', ascending=False)
    candidates = candidates[candidates['nom'].str.lower() != ingredient_name.lower()]
    
    if candidates.empty: return None, 0, "Pas de substitut"
    
    best = candidates.iloc[0]
    return best['nom'], int(best['score_temp'] * 100), best['desc']

# --- FONCTION OPENAI ---
def generate_recipe_with_ai(plat, contraintes, nb_personnes, key):
    # MODE SIMULATION SI PAS DE CLÉ
    if not key:
        time.sleep(1.5)
        return {
            "titre": f"{plat} (Mode Simulation)",
            "ingredients": [
                {"nom": "Pâtes (Simulation)", "qty": 100 * nb_personnes, "unit": "g", "sub": False},
                {"nom": "Crème de Cajou", "qty": 50 * nb_personnes, "unit": "ml", "sub": True, "org": "Crème Fraîche"},
            ],
            "etapes": ["Ceci est une simulation.", "Ajoutez une clé API valide pour voir la magie !"],
            "analyse": "Simulation de substitution faute de clé API."
        }

    # MODE RÉEL
    try:
        client = OpenAI(api_key=key)
        
        prompt = f"""
        Tu es Gus, un chef expert en cuisine inclusive.
        Plat demandé : {plat}
        Contraintes : {', '.join(contraintes)}
        Personnes : {nb_personnes}
        
        Génère une recette JSON stricte :
        {{
            "titre": "Nom recette",
            "ingredients": [
                {{"nom": "ingrédient", "qty": 10, "unit": "g", "sub": false, "org": null}}
            ],
            "etapes": ["Etape 1", "Etape 2"],
            "analyse": "Pourquoi ce choix ?"
        }}
        Si un ingrédient est remplacé pour respecter une contrainte, mets "sub": true et indique l'original dans "org".
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"titre": "Erreur API", "ingredients": [], "etapes": [f"Erreur: {str(e)}"], "analyse": "Erreur technique"}

# ================= INTERFACE PRINCIPALE =================

# 1. GESTION INTELLIGENTE DE LA CLÉ
# On regarde d'abord dans les secrets, sinon on demande à l'user.
api_key = st.secrets.get("OPENAI_KEY", None)

with st.sidebar:
    st.header("⚙️ Configuration")
    if api_key:
        st.success("✅ Clé API connectée via Secrets")
    else:
        api_key = st.text_input("Clé API OpenAI", type="password")
        if not api_key:
            st.warning("⚠️ Mode Simulation (Sans Clé)")
            st.info("Ajoutez votre clé dans les Secrets Streamlit pour l'activer définitivement.")

# 2. L'APPLICATION
col_spacer, col_main, col_spacer2 = st.columns([1, 3, 1])
with col_main:
    st.title("🍽️ Gus:Atlas")
    st.caption("Le guide culinaire inclusif.")

    with st.container(border=True):
        plat_input = st.text_input("Quelle envie aujourd'hui ?", placeholder="Ex: Risotto aux champignons")
        
        options_diet = ["Sans Gluten", "Sans Lactose", "Vegan", "Végétarien", "Sans Arachides", "Keto"]
        contraintes_input = st.multiselect("Vos Besoins & Envies", options_diet)
        
        if st.button("Lancer Gus 🚀", use_container_width=True):
            if plat_input:
                with st.status("Gus cuisine...", expanded=True):
                    st.write("🧠 Activation du modèle...")
                    result = generate_recipe_with_ai(plat_input, contraintes_input, 1, api_key)
                    st.session_state.recipe = result
                    st.write("✅ Recette prête !")

# 3. AFFICHAGE RÉSULTAT
if 'recipe' in st.session_state and st.session_state.recipe:
    recette = st.session_state.recipe
    
    st.divider()
    st.header(f"✨ {recette.get('titre', 'Résultat')}")
    
    if recette.get('ingredients'):
        col_g, col_d = st.columns([1, 2], gap="large")
        
        with col_g:
            st.subheader("Ingrédients")
            nb = st.number_input("Personnes", 1, 20, 2)
            st.markdown("---")
            for ing in recette['ingredients']:
                q = ing['qty'] * nb if isinstance(ing['qty'], (int, float)) else "?"
                if ing.get('sub'):
                    st.success(f"**{q} {ing['unit']} {ing['nom']}**")
                    st.caption(f"Remplace : {ing.get('org')}")
                else:
                    st.write(f"• {q} {ing['unit']} {ing['nom']}")
                    
        with col_d:
            st.subheader("Préparation")
            if 'analyse' in recette:
                st.info(recette['analyse'])
            for i, etape in enumerate(recette.get('etapes', [])):
                st.markdown(f"**{i+1}.** {etape}")
