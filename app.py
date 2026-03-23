import streamlit as st
import time
import os
import scraper
import exporter

# Configuration de la page
st.set_page_config(page_title="Scraper Annuaire Cameroun", page_icon="🇨🇲", layout="wide")

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
            
            # Limite pour éviter les blocages (similaire à ton ancien code)
            limit = 15
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
        
        # Aperçu des données
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
