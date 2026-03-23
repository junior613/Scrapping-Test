import streamlit as st
import os
import time

# Configuration de la page
st.set_page_config(page_title="Scraper Annuaire Cameroun", page_icon="🇨🇲", layout="wide")

# Vérification des dépendances et imports sécurisés
try:
    import pandas as pd
    import folium
    from streamlit_folium import st_folium
    import scraper
    import exporter
except ImportError as e:
    st.error(f"🛑 Une bibliothèque nécessaire est manquante : `{e.name}`")
    st.warning("Pour corriger ce problème, ouvrez votre terminal et lancez la commande suivante :")
    st.code("pip install -r requirements.txt", language="bash")
    st.stop()

EXPORT_DIR = os.path.join(os.getcwd(), "exports")
if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR)

@st.cache_data
def load_categories():
    """Charge les catégories avec le système de cache de Streamlit."""
    return scraper.get_categories()

def main():
    st.title("🇨🇲 Scraper GoAfricaOnline - Cameroun")
    st.markdown("Cette application permet d'extraire les coordonnées des entreprises.")

    # Chargement des catégories (sidebar)
    with st.sidebar:
        st.header("Configuration")
        if st.button("Rafraîchir les catégories"):
            st.cache_data.clear()
            
        with st.spinner("Chargement des catégories..."):
            categories = load_categories()
            
        if not categories:
            st.error("Impossible de charger les catégories.")
            return

        # Création d'un dictionnaire pour retrouver l'URL via le nom
        cat_dict = {cat['name']: cat['url'] for cat in categories}
        selected_cat_name = st.selectbox("Choisir une catégorie", options=list(cat_dict.keys()))
        selected_cat_url = cat_dict[selected_cat_name]
        
        max_pages = st.number_input("Nombre de pages à scraper", min_value=1, max_value=50, value=1)
        limit = st.slider("Limite d'entreprises à analyser (Détails + GPS)", min_value=1, max_value=100, value=15)
        
        start_scraping = st.button("Lancer le scraping", type="primary")

    # Zone principale
    if start_scraping:
        st.subheader(f"Traitement de : {selected_cat_name}")
        
        # Étape 1: Scrape listing
        with st.status("Récupération de la liste des entreprises...", expanded=True) as status:
            st.write(f"Scraping de {max_pages} pages sur {selected_cat_url}...")
            companies = scraper.scrape_category(selected_cat_url, max_pages=max_pages)
            
            if not companies:
                status.update(label="Aucune entreprise trouvée.", state="error")
                return
            
            st.write(f"✅ {len(companies)} entreprises trouvées.")
            
            # Étape 2: Détails (avec barre de progression)
            st.write("Récupération des détails (Site web, GPS)...")
            progress_bar = st.progress(0)
            
            companies_to_process = companies[:limit]
            
            for i, company in enumerate(companies_to_process):
                details = scraper.get_company_details(company['detail_url'])
                company.update(details)
                progress_bar.progress((i + 1) / len(companies_to_process))
                # Petit délai pour être gentil avec le serveur
                time.sleep(0.1) 
                
            status.update(label="Scraping terminé !", state="complete", expanded=False)

        # Étape 3: Export et Affichage
        st.success(f"Opération terminée. {len(companies_to_process)} fiches complétées.")
        
        # --- CARTE INTERACTIVE AVEC FOLIUM ---

        # 1. Filtrer les entreprises avec des coordonnées valides
        companies_with_coords = []
        for c in companies_to_process:
            coords = c.get('coords', 'N/A')
            if coords and coords != 'N/A' and ',' in str(coords):
                try:
                    lat, lon = map(float, coords.split(','))
                    c['lat'] = lat
                    c['lon'] = lon
                    companies_with_coords.append(c)
                except (ValueError, IndexError):
                    continue
        
        if not companies_with_coords:
            st.warning("Aucune coordonnée GPS trouvée pour afficher sur la carte.")
        else:
            # 2. Créer un selectbox pour choisir une entreprise
            company_names = ["- Vue d'ensemble -"] + [c['name'] for c in companies_with_coords]
            selected_name = st.selectbox("🎯 Choisir une entreprise pour la localiser", options=company_names)

            # 3. Déterminer le centre de la carte et le zoom
            map_center = [6, 12] # Centre approximatif du Cameroun
            map_zoom = 6
            selected_company_obj = None

            if selected_name != "- Vue d'ensemble -":
                selected_company_obj = next((c for c in companies_with_coords if c['name'] == selected_name), None)
                if selected_company_obj:
                    map_center = [selected_company_obj['lat'], selected_company_obj['lon']]
                    map_zoom = 17

            # 4. Créer et afficher la carte Folium
            st.subheader(f"📍 Carte interactive ({len(companies_with_coords)} localisées)")
            m = folium.Map(location=map_center, zoom_start=map_zoom, tiles="cartodbdark_matter")

            for company in companies_with_coords:
                popup_html = f"<b>{company['name']}</b>"
                if company.get('google_maps_url') and company['google_maps_url'] != 'N/A':
                    popup_html += f'<br><a href="{company["google_maps_url"]}" target="_blank">Ouvrir dans Google Maps</a>'
                
                is_selected = (selected_company_obj and company['name'] == selected_company_obj['name'])
                
                folium.Marker(
                    location=[company['lat'], company['lon']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=company['name'],
                    icon=folium.Icon(color='red' if is_selected else 'blue', icon='star' if is_selected else 'info-sign')
                ).add_to(m)

            st_folium(m, width=725, height=500)

        # Aperçu des données
        st.subheader("📋 Données brutes")
        st.dataframe(companies_to_process)
        
        # Export Excel
        filename, filepath = exporter.export_to_excel(companies_to_process, selected_cat_name, EXPORT_DIR)
        
        with open(filepath, "rb") as f:
            st.download_button(
                label="📥 Télécharger le fichier Excel",
                data=f,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == '__main__':
    main()
