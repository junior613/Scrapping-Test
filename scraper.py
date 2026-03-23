import requests
from bs4 import BeautifulSoup
import time
import re
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

BASE_URL = "https://www.goafricaonline.com" 
ANNUAIRE_URL = f"{BASE_URL}/cm/annuaire"

SCRAPPA_API_KEY = os.getenv("SCRAPPA_API_KEY")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def scrappa_request(url):
    """Effectue une requête directe (fallback) car Scrappa ne supporte pas l'URL universelle."""
    print(f"DEBUG: Requête vers {url}...")
    return requests.get(url, headers=HEADERS, timeout=10)

def get_categories():
    """Récupère la liste des catégories depuis la page principale."""
    # Liste de secours au cas où le site ne répond pas ou change de structure
    fallback_categories = [
        {"name": "BTP - Construction", "url": f"{BASE_URL}/cm/annuaire/batiment-btp"},
        {"name": "Informatique", "url": f"{BASE_URL}/cm/annuaire/informatique"},
        {"name": "Hôtels", "url": f"{BASE_URL}/cm/annuaire/hotels-hebergement"},
        {"name": "Transport & Logistique", "url": f"{BASE_URL}/cm/annuaire/transport-logistique"},
        {"name": "Services aux entreprises", "url": f"{BASE_URL}/cm/annuaire/services-entreprises"},
        {"name": "Agriculture", "url": f"{BASE_URL}/cm/annuaire/agriculture"},
        {"name": "Santé", "url": f"{BASE_URL}/cm/annuaire/sante"},
        {"name": "Alimentation", "url": f"{BASE_URL}/cm/annuaire/alimentation"},
        {"name": "Enseignement & Formation", "url": f"{BASE_URL}/cm/annuaire/enseignement-formation"},
        {"name": "Automobile", "url": f"{BASE_URL}/cm/annuaire/automobile-motos"}
    ]

    try:
        response = scrappa_request(ANNUAIRE_URL)
        response.raise_for_status()
        try:
            soup = BeautifulSoup(response.content, "lxml")
        except Exception:
            soup = BeautifulSoup(response.content, "html.parser")
        
        categories = []
        # Les catégories sont dans des colonnes de liens
        # On cherche les liens dans les sections de catégories
        cat_sections = soup.find_all("div", class_="w-full") # Hypothèse basée sur la structure courante
        
        # Chercher tous les liens qui contiennent '/cm/annuaire/'
        links = soup.find_all('a')
        for link in links:
            name = link.get_text(strip=True)
            href = link.get("href", "")
            
            # Si le lien est valide, n'est pas juste l'annuaire principal, et contient /cm/annuaire/
            if name and '/cm/annuaire/' in href and not href.endswith('/cm/annuaire'):
                # S'assurer qu'on gère bien les URLs absolues vs relatives
                full_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                categories.append({"name": name, "url": full_url})
        
        # Supprimer les doublons en gardant l'ordre
        seen = set()
        unique_categories = []
        for cat in categories:
            if cat["url"] not in seen:
                unique_categories.append(cat)
                seen.add(cat["url"])
        
        print(f"DEBUG: {len(unique_categories)} catégories trouvées en ligne.")
        if not unique_categories:
            print("DEBUG: Aucune catégorie trouvée, utilisation du fallback.")
            return fallback_categories
            
        return sorted(unique_categories, key=lambda x: x['name'])
    except Exception as e:
        print(f"ERREUR (Catégories): {e}. Utilisation de la liste de secours.")
        return fallback_categories

def scrape_category(category_url, max_pages=1):
    """Scrape les entreprises d'une catégorie donnée."""
    companies = []
    current_url = category_url
    
    for page in range(1, max_pages + 1):
        try:
            print(f"Scraping page {page}: {current_url}")
            response = scrappa_request(current_url)
            response.raise_for_status()
            try:
                soup = BeautifulSoup(response.content, "lxml")
            except Exception:
                soup = BeautifulSoup(response.content, "html.parser")
            
            # Rechercher les blocs d'entreprises
            # Sur GoAfricaOnline, elles sont souvent dans des <article> ou des div structurées
            listings = soup.select('article') or soup.select('.flex.flex-col.py-4')
            
            if not listings:
                break
                
            for item in listings:
                name_tag = item.select_one('h2 a') or item.select_one('h3 a')
                if not name_tag:
                    continue
                
                name = name_tag.get_text(strip=True)
                href = name_tag.get("href")
                detail_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                
                # Téléphone (souvent visible dans le listing)
                phone_tag = item.select_one('a[href^="tel:"]')
                phone = phone_tag.get_text(strip=True) if phone_tag else "N/A"
                
                company_data = {
                    "name": name,
                    "phone": phone,
                    "detail_url": detail_url,
                    "website": "N/A",
                    "coords": "Cameroun"
                }
                
                # Optionnel : Aller sur la fiche détail pour plus d'infos (Site web, etc.)
                # Pour éviter de bannir l'IP, on peut limiter les requêtes détails
                companies.append(company_data)
            
            # Pagination
            next_page = soup.select_one('a[rel="next"]')
            if next_page:
                href = next_page.get("href")
                current_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                time.sleep(1) # Respect du serveur
            else:
                break
                
        except Exception as e:
            print(f"Erreur sur la page {page} : {e}")
            break
            
    return companies

def get_company_details(detail_url):
    """Extrait les détails supplémentaires d'une entreprise."""
    try:
        response = scrappa_request(detail_url)
        response.raise_for_status()
        try:
            soup = BeautifulSoup(response.content, "lxml")
        except Exception:
            soup = BeautifulSoup(response.content, "html.parser")
        
        # Site web
        web_tag = soup.select_one('a[target="_blank"][rel*="nofollow"]')
        website = web_tag.get("href") if web_tag else "N/A"
        
        # Localisation (Coordonnées GPS depuis le lien Google Maps)
        map_link_tag = soup.select_one('a[href*="maps.google.com"]')
        location_coords = "N/A"
        google_maps_url = "N/A"
        if map_link_tag:
            map_href = map_link_tag.get("href")
            google_maps_url = map_href
            match = re.search(r'daddr=([\d.-]+,[\d.-]+)', map_href)
            if match:
                location_coords = match.group(1)
        
        return {
            "website": website,
            "coords": location_coords,
            "google_maps_url": google_maps_url
        }
    except Exception as e:
        print(f"Erreur détails {detail_url}: {e}")
        return {"website": "N/A", "coords": "N/A", "google_maps_url": "N/A"}

if __name__ == "__main__":
    # Test rapide
    cats = get_categories()
    print(f"Trouvé {len(cats)} catégories.")
    if cats:
        print(f"Test sur : {cats[0]['name']}")
        res = scrape_category(cats[0]['url'], max_pages=1)
        print(f"Trouvé {len(res)} entreprises.")
