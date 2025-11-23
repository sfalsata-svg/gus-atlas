import streamlit as st
import pandas as pd
import pickle
import time
import json
# On gère le cas où OpenAI n'est pas installé proprement
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
# On garde ça pour que l'app ne plante pas si le fichier manque,
# même si c'est l'IA qui fait le gros du travail maintenant.
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
    # 1. SÉCURITÉ : Pas de clé = Mode Simulation
    if not api_key:
        time.sleep(1)
        return {
            "titre": f"{plat} (Mode Démo)",
            "ingredients": [
                {"nom": "Pâtes", "qty": 100, "unit": "g", "sub": False},
                {"nom": "Crème Végétale (Démo)", "qty": 50, "unit": "ml", "sub": True, "org": "Crème"}
            ],
            "etapes": ["Veuillez ajouter une clé API Groq gratuite dans les secrets pour activer l'IA."],
            "analyse": "Mode démo activé."
        }

    # 2. CONNEXION À GROQ
    try:
        # L'astuce : On utilise le client OpenAI mais avec l'adresse de Groq
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key
        )
        
        # 3. LE PROMPT (L'instruction au chef)
        prompt = f"""
        Tu es Gus, un chef expert en cuisine moléculaire et inclusive.
        Objectif : Réinventer la recette du "{plat}" pour 1 personne.
        Contraintes strictes : {', '.join(contraintes) if contraintes else "Aucune"}.
        
        Instructions :
        1. Liste les ingrédients.
        2. Si un ingrédient viole une contrainte, remplace-le par une alternative intelligente (chimiquement proche).
        3. Réécris les étapes.
        
        IMPORTANT : Réponds UNIQUEMENT avec ce format JSON strict (sans texte avant ni après) :
        {{
            "titre": "Nom du plat revisité",
            "ingredients": [
                {{"nom": "Nom ingrédient", "qty": 100, "unit": "g/ml/cs", "sub": false, "org": null}},
                {{"nom": "Nom substitut", "qty": 50, "unit": "g", "sub": true, "org": "Nom ingrédient remplacé"}}
            ],
            "etapes": ["Etape 1...", "Etape 2..."],
            "analyse": "Explication courte du changement majeur."
        }}
        """
        
        # 4. APPEL DU MODÈLE (Llama 3 est gratuit et très puissant)
        response = client.chat.completions.create(
            model="llama3-8b-8192", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        
        # 5. NETTOYAGE DE LA RÉPONSE (Parsing JSON)
        content = response.choices[0].message.content
        # On cherche les accolades pour être sûr de n'avoir que le JSON
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("L'IA n'a pas renvoyé de JSON valide.")
            
        json_str = content[start_idx:end_idx]
        return json.loads(json_str)

    except Exception as e:
        return {
            "titre": "Erreur Technique", 
            "ingredients": [], 
            "etapes": [f"Détail de l'erreur : {str(e)}"], 
            "analyse": "Impossible de générer la recette."
        }

# ================= INTERFACE UTILISATEUR =================

# --- 1. GESTION DE LA CLÉ API ---
# On regarde en priorité dans les Secrets (c'est là que tu as mis ta clé Groq)
api_key = st.secrets.get("OPENAI_KEY", None)

with st.sidebar:
    st.header("⚙️ Configuration")
    if api_key:
        st.success("✅ Moteur IA Connecté")
        st.caption("Modèle : Llama3 (via Groq)")
    else:
        st.warning("⚠️ Pas de clé détectée")
        st.info("Ajoutez votre clé Groq dans les Secrets Streamlit (OPENAI_KEY).")
        api_key = st.text_input("Ou collez-la ici (temporaire)", type="password")

# --- 2. HEADER & INPUTS ---
col_spacer, col_main, col_spacer2 = st.columns([1, 3, 1])

with col_main:
    st.title("🍽️ Gus:Atlas")
    st.markdown("**Le guide culinaire inclusif.** *Tapez n'importe quel plat, Gus l'adapte.*")

    with st.container(border=True):
        col_input1, col_input2 = st.columns([2, 1])
        
        with col_input1:
            plat_input = st.text_input("Quelle recette voulez-vous ?", placeholder="Ex: Boeuf Bourguignon, Tarte au citron...")
        
        with col_input2:
            options_diet = [
                "Sans Gluten", "Sans Lactose", "Vegan", "Végétarien", 
                "Sans Arachides", "Sans Fruits à coque", "Sans Porc", 
                "Keto", "Low FODMAP", "Sans Soja", "Sans Oeufs"
            ]
            contraintes_input = st.multiselect("Contraintes", options_diet)
        
        # Bouton d'action centré
        if st.button("Lancer Gus 🚀", use_container_width=True):
            if plat_input:
                st.session_state.current_recipe = None # Reset
                
                with st.status("👨‍🍳 Gus est en cuisine...", expanded=True) as status:
                    st.write("🧠 Analyse moléculaire des ingrédients...")
                    time.sleep(0.5)
                    st.write("🔍 Recherche de substituts dans la base vectorielle...")
                    
                    # Appel de la fonction IA
                    result = generate_recipe_with_groq(plat_input, contraintes_input, 1, api_key)
                    
                    st.session_state.current_recipe = result
                    status.update(label="C'est prêt !", state="complete", expanded=False)

# --- 3. AFFICHAGE DES RÉSULTATS ---
if 'current_recipe' in st.session_state and st.session_state.current_recipe:
    recette = st.session_state.current_recipe
    
    st.divider()
    
    # Titre du plat
    st.markdown(f"<h2 style='text-align: center;'>✨ {recette.get('titre', 'Recette')}</h2>", unsafe_allow_html=True)
    
    # Analyse du chef (Pourquoi ce changement ?)
    if recette.get('analyse'):
        st.info(f"💡 **Note du Chef Gus :** {recette['analyse']}")
    
    col_g, col_d = st.columns([1, 2], gap="large")
    
    # Colonne Gauche : Ingrédients dynamiques
    with col_g:
        st.subheader("Ingrédients")
        
        # Sélecteur de portions
        nb_pers = st.number_input("Nombre de personnes", min_value=1, max_value=50, value=2)
        st.markdown("---")
        
        if recette.get('ingredients'):
            for ing in recette['ingredients']:
                # Calcul de la quantité x Nombre de personnes
                try:
                    qte = float(ing['qty']) * nb_pers
                    # On enlève les décimales inutiles (ex: 200.0 -> 200)
                    if qte.is_integer(): qte = int(qte)
                except:
                    qte = "?"
                
                unit = ing['unit']
                nom = ing['nom']
                
                # Affichage différent si c'est un substitut
                if ing.get('sub'):
                    st.markdown(f"""
                    <div class="success-box">
                        <b>✅ {qte} {unit} {nom}</b><br>
                        <small><i>Remplace : {ing.get('org')}</i></small>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.write(f"• **{qte} {unit}** {nom}")
        else:
            st.write("Aucun ingrédient trouvé.")

    # Colonne Droite : Etapes
    with col_d:
        st.subheader("Préparation")
        if recette.get('etapes'):
            for i, etape in enumerate(recette['etapes']):
                st.markdown(f"**{i+1}.** {etape}")
                st.write("") # Petit espace
        else:
            st.warning("Pas d'étapes générées.")
