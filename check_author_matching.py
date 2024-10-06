import csv
import os
import pandas as pd
import numpy as np
from scholarly import scholarly
import time
import random

def get_author_id(author_name):
    try:
        search_query = scholarly.search_author(author_name)
        author = next(search_query)
        return author['scholar_id']
    except StopIteration:
        return "NA"
    except Exception as e:
        print(f"Error searching for author {author_name}: {e}")
        return "NA"

def count_non_empty(s):
    if pd.isna(s):  # Check if the value is NaN
        return 0
    if not isinstance(s, str):  # If it's not a string, convert it to one
        s = str(s)
    return len([x for x in s.split(', ') if x.strip() != '' and x.strip() != 'NA'])

def check_author_matching(input_file):
    # Try different parsing options
    try:
        # First attempt: standard CSV reading
        df = pd.read_csv(input_file)
    except pd.errors.ParserError:
        try:
            # Second attempt: read with quoted fields
            df = pd.read_csv(input_file, quoting=csv.QUOTE_ALL)
        except pd.errors.ParserError:
            try:
                # Third attempt: read with different delimiter
                df = pd.read_csv(input_file, sep='\t')  # Try tab as delimiter
            except pd.errors.ParserError:
                # If all attempts fail, read the file manually
                with open(input_file, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                    # Print the problematic line and surrounding lines
                    print("Problematic lines:")
                    for i in range(max(0, 1), min(len(lines), 5)):  # Print lines 1-5
                        print(f"Line {i + 1}: {lines[i].strip()}")
                raise ValueError(f"Unable to parse the CSV file: {input_file}")

    # Apply the function to both columns
    df['author_count'] = df['citing_authors'].apply(lambda x: len(str(x).split(', ')) if pd.notna(x) else 0)
    df['id_count'] = df['citing_author_id'].apply(count_non_empty)

    # Create the 'match_status' column
    df['match_status'] = df.apply(lambda row: 'matched' if row['author_count'] == row['id_count'] else 'unmatched', axis=1)

    # Function to retrieve missing author IDs
    def get_missing_ids(row):
        if row['match_status'] == 'unmatched':
            authors = str(row['citing_authors']).split(', ') if pd.notna(row['citing_authors']) else []
            ids = str(row['citing_author_id']).split(', ') if pd.notna(row['citing_author_id']) else []
            new_ids = []
            for author, id in zip(authors, ids + [''] * (len(authors) - len(ids))):
                if not id or id == 'NA':
                    print(f"Searching for ID of author: {author}")
                    new_id = get_author_id(author)
                    new_ids.append(new_id)
                    print(f"Result for {author}: {new_id}")
                else:
                    new_ids.append(id)
                time.sleep(random.uniform(1, 3))  # Add delay to avoid rate limiting
            return ', '.join(new_ids)
        return row['citing_author_id']

    # Apply the function to retrieve missing author IDs
    df['citing_author_id'] = df.apply(get_missing_ids, axis=1)

    # Recheck the match status, considering NA as unmatched
    df['author_count'] = df['citing_authors'].apply(lambda x: len(str(x).split(', ')) if pd.notna(x) else 0)
    df['id_count'] = df['citing_author_id'].apply(count_non_empty)
    df['match_status'] = df.apply(lambda row: 'matched' if row['author_count'] == row['id_count'] else 'unmatched', axis=1)

    # Drop the temporary counting columns
    df = df.drop(columns=['author_count', 'id_count'])

    # Reorder columns to put match_status first
    columns = ['match_status'] + [col for col in df.columns if col != 'match_status']
    df = df[columns]

    # Create output filename
    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}_checked_with_ids.csv"

    # Save the result
    df.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")

    # Print summary
    total_rows = len(df)
    matched_rows = (df['match_status'] == 'matched').sum()
    unmatched_rows = total_rows - matched_rows
    print(f"\nSummary for {os.path.basename(input_file)}:")
    print(f"Total rows: {total_rows}")
    print(f"Matched rows: {matched_rows}")
    print(f"Unmatched rows: {unmatched_rows}")

def main():
    input_folder = "/Users/lilyzhang/Desktop/Demo/CitationMap/citations_la-Mx-UAAAAJ"
    
    if not os.path.exists(input_folder):
        print(f"Error: Folder {input_folder} not found.")
        return

    csv_files = [f for f in os.listdir(input_folder) if f.endswith('.csv') and not f.endswith('_checked_with_ids.csv')]

    for csv_file in csv_files:
        input_file = os.path.join(input_folder, csv_file)
        print(f"\nProcessing file: {csv_file}")
        check_author_matching(input_file)

if __name__ == "__main__":
    main()