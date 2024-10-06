import csv
from typing import List, Dict

def read_csv(file_path: str) -> List[Dict]:
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)

def write_csv(file_path: str, data: List[Dict], fieldnames: List[str]):
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def flatten_authors(input_file: str, output_file: str):
    data = read_csv(input_file)
    flattened_data = []

    for row in data:
        authors = row['citing_author_names'].split(', ')
        author_ids = row['citing_author_id'].split(', ')

        for i, author in enumerate(authors):
            flattened_row = {
                'citing_author_name': author,
                'citing_author_id': author_ids[i] if i < len(author_ids) else 'NA',
                'match_status': row['match_status'],
                'source_paper': row['source_title'],
                'citing_year': row['citing_year'],
                'cited_paper': row['citing_title'],
                'citedby_url': row['citedby_url'],
                'citing_url': row['citing_url']
            }
            flattened_data.append(flattened_row)

    fieldnames = ['citing_author_name', 'citing_author_id', 'match_status', 
                  'citing_year', 'cited_paper', 'source_paper', 'citedby_url',   'citing_url']
    
    write_csv(output_file, flattened_data, fieldnames)
    print(f"Flattened data saved to {output_file}")

if __name__ == "__main__":
    input_file = 'CitationMap/status_checked/combined_citations.csv'
    output_file = 'CitationMap/status_checked/flattened_authors.csv'
    flatten_authors(input_file, output_file)