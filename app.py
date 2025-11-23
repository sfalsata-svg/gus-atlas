import streamlit as st
import pandas as pd
import pickle
import time
import json
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Gus:Atlas", page_icon="🍽️")

# --- CSS PERSONNALISÉ ---
st.markdown("""
<style>
    .stTextInput input {border-radius: 20px; padding: 10px;}
    .stMultiSelect span {border-radius: 10px;}
    div[data-testid="stMetricValue"] {font-size: 1.2rem;}
</style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DU CERVEAU (VECTEURS) ---
@st.cache_data
def load_brain():
    try:
        with open('gus_brain.pkl', 'rb') as f:
            return pickle.load(f)
    except:
        return pd.DataFrame() # Retourne vide si erreur pour pas planter

df_ingredients = load_brain()

# --- FONCTION INTELLIGENTE (GUS) ---
def get_smart_substitute(ingredient_name, forbidden_categories):
    # Logique simplifiée pour la démo : On cherche le meilleur vecteur
    if df_ingredients.empty: return None, 0, "Base de données non chargée"
    
    row = df_ingredients[df_ingredients['nom'].str.lower() == ingredient_name.lower()]
    if row.empty: return None, 0, "Ingrédient inconnu"
    
    target_vector = row['vector'].values[0]
    scores = cosine_similarity([target_vector], list(df_ingredients['vector']))[0]
    df_ingredients['score_temp'] = scores
    
    # On trie et on exclut l'ingrédient lui-même
    candidates = df_ingredients.sort_values(by='score_temp', ascending=False)
    candidates = candidates[candidates['nom'].str.lower() != ingredient_name.lower()]
    
    # ICI: Dans une version avancée, on filtrerait selon "forbidden_categories"
    # Pour l'instant, on prend le top 1
    best = candidates.iloc[0]
    return best['nom'], int(best['score_temp'] * 100), best['desc']

# --- CONNEXION OPENAI (IA GÉNÉRATIVE) ---
def generate_recipe_with_ai(plat, contraintes, nb_personnes, api_key):
    if not api_key:
        # MODE SECOURS (Si pas de clé API)
        time.sleep(2)
        return {
            "titre": f"{plat} (Mode Simulation)",
            "ingredients": [
                {"nom": "Pâtes", "qty": 100 * nb_personnes, "unit": "g", "sub": False},
                {"nom": "Crème de Cajou", "qty": 50 * nb_personnes, "unit": "ml", "sub": True, "org": "Crème Fraîche"},
            ],
            "etapes": ["Ceci est une simulation car la clé API est absente.", "Ajoutez une clé pour avoir la vraie recette !"],
            "analyse": "Simulation de substitution."
        }

    client = OpenAI(api_key=api_key)
    
    # Prompt pour l'IA : On lui demande du JSON structuré
    prompt = f"""
    Agis comme un chef expert en adaptation culinaire.
    Le client veut : {plat}.
    Ses contraintes strictes sont : {', '.join(contraintes)}.
    Nombre de personnes : {nb_personnes}.
    
    Tâche :
    1. Identifie les ingrédients problématiques de la recette traditionnelle.
    2. Remplace-les pour respecter les contraintes.
    3. Génère la recette complète adaptée.
    
    Réponds UNIQUEMENT au format JSON strict comme suit :
    {{
        "titre": "Nom du plat adapté",
        "ingredients": [
            {{"nom": "Nom ingrédient", "qty": quantité_numérique_pour_1_pers, "unit": "g/ml/pincee", "sub": true/false, "org": "Ingrédient remplacé si sub"}}
        ],
        "etapes": ["Etape 1", "Etape 2"],
        "analyse": "Explication courte de pourquoi tel changement a été fait."
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", # Ou gpt-4o si tu as accès
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except:
        return None

# --- GESTION ÉTAT ---
if 'recipe' not in st.session_state: st.session_state.recipe = None
if 'inputs' not in st.session_state: st.session_state.inputs = {}

# ================= INTERFACE =================

# Sidebar pour la clé API (Discret)
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Clé API OpenAI", type="password", help="Nécessaire pour le mode 'Sans Limite'")
    st.info("Sans clé, le mode démo sera activé.")

# HEADER
col_spacer, col_main, col_spacer2 = st.columns([1, 3, 1])
with col_main:
    st.title("🍽️ Gus:Atlas")
    st.write("Le guide culinaire inclusif.")

# INPUTS (Toujours visibles en haut)
with st.container(border=True):
    c1, c2 = st.columns([2, 1])
    
    with c1:
        plat_input = st.text_input("Quelle envie aujourd'hui ?", placeholder="Ex: Risotto aux champignons, Tiramisu...")
    
    with c2:
        # NOUVEAU : Multiselect pour contraintes illimitées
        options_diet = [
            "Sans Gluten", "Sans Lactose", "Vegan", "Végétarien", 
            "Sans Arachides", "Sans Fruits à coque", "Sans Porc", 
            "Keto", "Low FODMAP", "Sans Soja", "Sans Oeufs"
        ]
        contraintes_input = st.multiselect("Vos Besoins & Envies", options_diet)

    if st.button("Lancer Gus 🚀", use_container_width=True):
        if plat_input:
            with st.status("Gus est en cuisine...", expanded=True) as status:
                st.write("🧠 Analyse de la demande...")
                time.sleep(1)
                st.write("🔍 Recherche vectorielle des substituts...")
                # C'est ici qu'on appelle la vraie IA
                result = generate_recipe_with_ai(plat_input, contraintes_input, 1, api_key)
                st.session_state.recipe = result
                st.session_state.inputs = {"plat": plat_input, "contraintes": contraintes_input}
                status.update(label="Recette prête !", state="complete", expanded=False)

# RESULTATS
if st.session_state.recipe:
    recette = st.session_state.recipe
    
    st.divider()
    
    # Titre dynamique
    st.header(f"✨ {recette.get('titre', 'Recette')}")
    if 'analyse' in recette:
        st.info(f"💡 **Note du Chef Gus :** {recette['analyse']}")
    
    col_g, col_d = st.columns([1, 2], gap="large")
    
    with col_g:
        st.subheader("Ingrédients")
        # GESTION DES QUANTITÉS
        nb_pers = st.number_input("Nombre de personnes", min_value=1, value=2, step=1)
        
        st.write("---")
        for ing in recette['ingredients']:
            # Calcul mathématique simple
            qte_finale = ing['qty'] * nb_pers if isinstance(ing['qty'], (int, float)) else ing['qty']
            
            # Affichage visuel
            if ing.get('sub'):
                st.markdown(f"🟢 **{qte_finale} {ing['unit']} {ing['nom']}**")
                st.caption(f"*(Remplace : {ing.get('org', 'Inconnu')})*")
            else:
                st.markdown(f"• {qte_finale} {ing['unit']} {ing['nom']}")
                
    with col_d:
        st.subheader("Préparation")
        steps = recette.get('etapes', [])
        for idx, etape in enumerate(steps):
            st.markdown(f"**{idx+1}.** {etape}")
