import csv
from scholarly import scholarly, ProxyGenerator
import time
import random
from fuzzywuzzy import fuzz
import re

def clean_author_name(name):
    # Split the name into last and first parts
    parts = name.strip().split(',', 1)
    if len(parts) == 2:
        last_name, first_name = parts
        # Clean up any extra spaces
        last_name = last_name.strip()
        first_name = first_name.strip()
        # Return in "First Last" format
        return f"{first_name} {last_name}"
    return name.strip()

def setup_scholarly():
    pg = ProxyGenerator()
    pg.ScraperAPI("78958c46d9c2b2d8729d25bbb48b7706")
    scholarly.use_proxy(pg)

def search_paper(paper_title, max_retries=3):
    for attempt in range(max_retries):
        try:
            search_query = scholarly.search_pubs(paper_title)
            best_match = None
            best_score = 0

            for result in search_query:
                filled_result = scholarly.fill(result)
                title_score = fuzz.ratio(paper_title.lower(), filled_result['bib']['title'].lower())
                
                if title_score > best_score:
                    best_match = filled_result
                    best_score = title_score

                if best_score >= 95:  # If we find a very good match, stop searching
                    break

            if best_match:
                # Get raw author names and clean them
                print(best_match['bib'])
                raw_authors = best_match['bib'].get('author', '')
                # Split the author string by 'and' and clean each name
                author_list = [name.strip() for name in raw_authors.split(' and ')]
                authors = [clean_author_name(author) for author in author_list]
                # Filter out empty strings
                authors = [author for author in authors if author.strip()]
                
                return {
                    'title': best_match['bib']['title'],
                    'authors': '; '.join(authors),
                    'author_ids': '; '.join(best_match.get('author_id', ['N/A']))
                }
            return None

        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.random()
                print(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Skipping this paper.")
                return None

def process_judged_papers(input_csv, output_csv):
    setup_scholarly()
    results = []

    # Read input papers
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        papers = list(reader)

    total_papers = len(papers)
    print(f"Processing {total_papers} papers...")

    for i, paper in enumerate(papers, 1):
        print(f"\nProcessing paper {i}/{total_papers}")
        print(f"Title: {paper['paper_title']}")
        
        paper_info = search_paper(paper['paper_title'])
        
        if paper_info:
            print("Found paper information:")
            print(f"Authors: {paper_info['authors']}")
            print(f"Author IDs: {paper_info['author_ids']}")
            results.append({
                'paper_title': paper['paper_title'],
                'authors': paper_info['authors'],
                'author_ids': paper_info['author_ids']
            })
        else:
            print("No results found. Recording with empty author information.")
            results.append({
                'paper_title': paper['paper_title'],
                'authors': '',
                'author_ids': ''
            })
        
        # Add delay to avoid rate limiting
        time.sleep(random.uniform(2, 4))

    # Write results to output file
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['paper_title', 'authors', 'author_ids']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults have been saved to {output_csv}")

if __name__ == "__main__":
    input_csv = "citation_map/judged_authors_short.csv"
    output_csv = "citation_map/judged_authors_short_with_details.csv"
    process_judged_papers(input_csv, output_csv) 
