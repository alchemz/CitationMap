import csv
from scholarly import scholarly, ProxyGenerator
import time
from tqdm import tqdm

SCRAPER_API_KEY = "78958c46d9c2b2d8729d25bbb48b7706"

def setup_proxy():
    # pg = ProxyGenerator()
    # success = pg.ScraperAPI(SCRAPER_API_KEY, country_code='fr', premium=True, render=True)
    # scholarly.use_proxy(pg)
    pg = ProxyGenerator()
    success = pg.FreeProxies()
    scholarly.use_proxy(pg)
    if success:
        print("Proxy setup successful")
    else:
        print("Proxy setup failed")

def extract_conference_from_scholarly(title):
    print(f"Searching for: {title}")
    search_query = scholarly.search_pubs(title)
    publication = next(search_query)
    try:
        filled_publication = scholarly.fill(publication)
        print("Publication found and filled:")
        # scholarly.bibtex(pub)
        # scholarly.pprint(filled_publication)
        scholarly.pprint(filled_publication)
        venue = filled_publication['bib'].get('venue', '')
        if venue:
            if 'Proceedings' in venue:
                return f"Conference: {venue}"
            elif 'Journal' in venue:
                return f"Journal: {venue}"
            return f"Venue: {venue}"
        
        print("No venue found in this result")
    except StopIteration:
        print("No publication found")
    except Exception as e:
        print(f"Error processing {title}: {str(e)}")
    return 'Unknown'

def add_conference_column(input_file, output_file):
    with open(input_file, 'r', newline='', encoding='utf-8') as infile, \
         open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['venue']
        
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in tqdm(reader, desc="Processing citations"):
            title = row['citing_title']
            venue = extract_conference_from_scholarly(title)
            row['venue'] = venue
            writer.writerow(row)
            
            print(f"Title: {title[:50]}...")
            print(f"Venue: {venue}")
            print("-" * 50)
            
            # Add a small delay to avoid overwhelming the API
            time.sleep(1)
    
    print(f"\nVenue information added. Output saved to {output_file}")

if __name__ == "__main__":
    setup_proxy()
    input_file = '/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/citations_LANe:_Lighting-Aware_Neural_Fields_for_Composition_checked_with_ids.csv'
    output_file = '/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/citations_LANe_with_venue.csv'
    
    add_conference_column(input_file, output_file)