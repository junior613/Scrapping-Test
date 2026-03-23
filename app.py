import streamlit as st
from flask import Flask, render_template, request, send_from_directory, jsonify
import os
import scraper
import exporter
import threading

app = Flask(__name__)
EXPORT_DIR = os.path.join(os.getcwd(), "exports")
if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR)

# Cache pour les catégories
categories_cache = []

@app.route('/')
def index():
    global categories_cache
    if not categories_cache:
        categories_cache = scraper.get_categories()
    return render_template('index.html', categories=categories_cache)

@app.route('/scrape', methods=['POST'])
def run_scrape():
    category_url = request.form.get('category_url')
    category_name = request.form.get('category_name')
    max_pages = int(request.form.get('max_pages', 1))
    
    if not category_url:
        return jsonify({"error": "URL de catégorie manquante"}), 400
        
    try:
        # Étape 1: Scrape les entreprises (listing)
        companies = scraper.scrape_category(category_url, max_pages=max_pages)
        
        # Étape 2: Récupère les détails (Site web, etc.)
        # Limité à 10 pour le test rapide ou selon le besoin
        for company in companies[:15]: # Limite pour éviter les blocages lors des tests
            details = scraper.get_company_details(company['detail_url'])
            company.update(details)
            
        # Étape 3: Export Excel
        filename, filepath = exporter.export_to_excel(companies, category_name)
        
        return jsonify({
            "success": True,
            "count": len(companies),
            "filename": filename,
            "companies": companies
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(EXPORT_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
