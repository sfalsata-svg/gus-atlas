import streamlit as st
import pandas as pd
import pickle
import time
import json
import os

# Gestion propre de l'import OpenAI
try:
    from openai import OpenAI
except ImportError:
    st.error("⚠️ Le module 'openai' manque. Ajoutez-le dans requirements.txt")
    st.stop()

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Gus:Atlas", page_icon="🍽️")

# --- STYLE CSS (DESIGN) ---
st.markdown("""
<style>
    .stTextInput input {border-radius: 20px; padding: 10px;}
    .stMultiSelect span {border-radius: 10px;}
    div[data-testid="stMetricValue"] {font-size: 1.2rem;}
    .success-box {padding:10px; border-radius:10px; background-color:#d4edda; color:#155724; margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DU CERVEAU (Fichier Kaggle) ---
@st.cache_data
def load_brain():
    try:
        with open('gus_brain.pkl', 'rb') as f:
            return pickle.load(f)
    except:
        return pd.DataFrame() 

df_ingredients = load_brain()

# --- FONCTION D'INTELLIGENCE (VIA GROQ) ---
def generate_recipe_with_groq(plat, contraintes, nb_personnes, api_key):
    # 1. SÉCURITÉ
    if not api_key:
        time.sleep(1)
        return {
            "titre": "Mode Démo (Pas de clé)",
            "ingredients": [],
            "etapes": ["Veuillez ajouter une clé API Groq."],
            "analyse": "Clé manquante."
        }

    # 2. CONNEXION À GROQ
    try:
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key
        )
        
        # 3. LE PROMPT
        prompt = f"""
        Tu es Gus, un chef expert.
        Objectif : Réinventer la recette du "{plat}" pour 1 personne.
        Contraintes : {', '.join(contraintes) if contraintes else "Aucune"}.
        
        Instructions :
        1. Liste les ingrédients.
        2. Si un ingrédient est interdit, remplace-le par une alternative.
        3. Réécris les étapes.
        
        Format JSON strict attendu :
        {{
            "titre": "Nom du plat revisité",
            "ingredients": [
                {{"nom": "Nom ingrédient", "qty": 100, "unit": "g", "sub": false, "org": null}},
                {{"nom": "Nom substitut", "qty": 50, "unit": "g", "sub": true, "org": "Original"}}
            ],
            "etapes": ["Etape 1...", "Etape 2..."],
            "analyse": "Explication du changement."
        }}
        """
        
        # 4. APPEL DU MODÈLE (MISE À JOUR ICI : Llama 3.3)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1024
        )
        
        # 5. NETTOYAGE DE LA RÉPONSE
        content = response.choices[0].message.content
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        
        if start_idx == -1:
            raise ValueError("Erreur de format JSON")
            
        json_str = content[start_idx:end_idx]
        return json.loads(json_str)

    except Exception as e:
        return {
            "titre": "Oups !", 
            "ingredients": [], 
            "etapes": [f"Erreur technique : {str(e)}"], 
            "analyse": "Impossible de générer la recette."
        }

# ================= INTERFACE UTILISATEUR =================

# --- 1. GESTION DE LA CLÉ API ---
api_key = st.secrets.get("OPENAI_KEY", None)

with st.sidebar:
    st.header("⚙️ Configuration")
    if api_key:
        st.success("✅ Moteur IA Connecté")
        st.caption("Modèle : Llama 3.3 (Groq)")
    else:
        st.warning("⚠️ Pas de clé détectée")
        st.info("Ajoutez votre clé dans les Secrets.")

# --- 2. HEADER & INPUTS ---
col_spacer, col_main, col_spacer2 = st.columns([1, 3, 1])

with col_main:
    st.title("🍽️ Gus:Atlas")
    st.markdown("**Le guide culinaire inclusif.**")

    with st.container(border=True):
        col_input1, col_input2 = st.columns([2, 1])
        with col_input1:
            plat_input = st.text_input("Quelle recette voulez-vous ?", placeholder="Ex: Boeuf Bourguignon")
        with col_input2:
            options_diet = ["Sans Gluten", "Sans Lactose", "Vegan", "Végétarien", "Sans Arachides", "Keto", "Low FODMAP"]
            contraintes_input = st.multiselect("Contraintes", options_diet)
        
        if st.button("Lancer Gus 🚀", use_container_width=True):
            if plat_input:
                st.session_state.current_recipe = None
                with st.status("👨‍🍳 Gus cuisine...", expanded=True) as status:
                    st.write("🧠 Activation de Llama-3.3...")
                    result = generate_recipe_with_groq(plat_input, contraintes_input, 1, api_key)
                    st.session_state.current_recipe = result
                    status.update(label="C'est prêt !", state="complete", expanded=False)

# --- 3. AFFICHAGE DES RÉSULTATS ---
if 'current_recipe' in st.session_state and st.session_state.current_recipe:
    recette = st.session_state.current_recipe
    
    st.divider()
    st.markdown(f"<h2 style='text-align: center;'>✨ {recette.get('titre', 'Recette')}</h2>", unsafe_allow_html=True)
    
    if recette.get('analyse'):
        st.info(f"💡 **Note du Chef Gus :** {recette['analyse']}")
    
    col_g, col_d = st.columns([1, 2], gap="large")
    
    with col_g:
        st.subheader("Ingrédients")
        nb_pers = st.number_input("Nombre de personnes", 1, 50, 2)
        st.markdown("---")
        
        if recette.get('ingredients'):
            for ing in recette['ingredients']:
                try:
                    qte = float(ing['qty']) * nb_pers
                    if qte.is_integer(): qte = int(qte)
                except: qte = "?"
                
                if ing.get('sub'):
                    st.markdown(f"""
                    <div class="success-box">
                        <b>✅ {qte} {ing['unit']} {ing['nom']}</b><br>
                        <small><i>Remplace : {ing.get('org')}</i></small>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.write(f"• **{qte} {ing['unit']}** {ing['nom']}")

    with col_d:
        st.subheader("Préparation")
        if recette.get('etapes'):
            for i, etape in enumerate(recette['etapes']):
                st.markdown(f"**{i+1}.** {etape}")
                st.write("")
        else:
            st.warning(f"Erreur : {recette.get('etapes')}")
