import requests
from scholarly import scholarly, ProxyGenerator
import csv
import time
import random
import os
import re

# Replace with your ScraperAPI key
SCRAPER_API_KEY = ''

def format_author_name(author):
    parts = author.split(', ')
    if len(parts) > 1:
        return f"{parts[1]} {parts[0]}"
    return author

def format_author_list(authors):
    author_list = authors.split(' and ')
    return ', '.join(format_author_name(author.strip()) for author in author_list)

def get_citations_for_author(author_id):
    print(f"Retrieving citations for author ID: {author_id}")
    
    pg = ProxyGenerator()
    pg.ScraperAPI(SCRAPER_API_KEY)
    scholarly.use_proxy(pg)
    
    try:
        author = scholarly.search_author_id(author_id)
        author = scholarly.fill(author)
    except Exception as e:
        print(f"Error retrieving author: {str(e)}")
        return None, []
    
    all_citations = []
    author_dir = f"citations_{author_id}"
    os.makedirs(author_dir, exist_ok=True)
    
    pub = author['publications'][0]
    print(f"Processing the first publication")
    try:
        filled_pub = scholarly.fill(pub)
        
        pub_citations = []
        citedby = scholarly.citedby(filled_pub)
        for citation in citedby:
            citation = scholarly.fill(citation)
            if isinstance(citation, dict):
                citation_info = {
                    'source_title': filled_pub['bib']['title'],
                    'citedby_url': filled_pub.get('citedby_url', 'N/A'),
                    'citing_year': citation['bib'].get('pub_year', 'N/A'),
                    'citing_title': citation['bib']['title'],
                    'citing_authors': format_author_list(citation['bib']['author']),
                    'citing_author_id': ', '.join(citation.get('author_id', [])),
                    'citing_url': citation.get('pub_url', 'N/A'),
                }
            else:
                citation_info = {
                    'source_title': filled_pub['bib']['title'],
                    'citedby_url': filled_pub.get('citedby_url', 'N/A'),
                    'citing_year': 'N/A',
                    'citing_title': citation,
                    'citing_authors': 'N/A',
                    'citing_author_id': 'N/A',
                    'citing_url': 'N/A',
                }
            pub_citations.append(citation_info)
            print(f"Processed citation: {citation_info['citing_title']}")
            print(f"Citing authors: {citation_info['citing_authors']}")
            print(f"Citing URL: {citation_info['citing_url']}")
        
        all_citations.extend(pub_citations)
        print(f"Found {len(pub_citations)} citations for: {filled_pub['bib']['title']}")
        print(f"Citedby URL: {filled_pub.get('citedby_url', 'N/A')}")
        
        pub_title = filled_pub['bib']['title'][:50].replace(" ", "_")
        output_filename = os.path.join(author_dir, f"citations_{pub_title}.csv")
        save_citations_to_csv(pub_title, pub_citations, output_filename)
        
    except Exception as e:
        print(f"Error processing publication: {str(e)}")
    
    return author['name'], all_citations

def save_citations_to_csv(pub_title, citations, output_filename):
    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['source_title', 'citedby_url', 'citing_year', 'citing_title', 'citing_authors', 'citing_author_id', 'citing_url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        
        writer.writeheader()
        for citation in citations:
            writer.writerow(citation)
    
    print(f"Citation data for '{pub_title}' has been saved to {output_filename}")

def main():
    # author_id = "la-Mx-UAAAAJ"  # Replace with the desired author ID
    # author_id = "ifybhH8AAAAJ" 
    author_id = 'ZYvXHYwAAAAJ'
    
    print("Starting citation retrieval...")
    author_name, all_citations = get_citations_for_author(author_id)
    if author_name:
        print(f"Citation retrieval complete for author: {author_name}")
        print(f"CSV files have been saved in the directory: citations_{author_id}")
    else:
        print("Failed to retrieve citations.")

if __name__ == "__main__":
    main()