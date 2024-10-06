import sys
import os
import warnings
import pandas as pd
import glob

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Add the parent directory of 'CitationMap' to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from citation_map.citation_map import generate_citation_map

if __name__ == '__main__':
    scholar_id = 'la-Mx-UAAAAJ'
    flattened_authors_path = '/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/flattened_authors.csv'

    if not os.path.isfile(flattened_authors_path):
        print(f"Error: {flattened_authors_path} does not exist.")
        sys.exit(1)

    generate_citation_map(scholar_id, output_path='citation_map.html',
                          cache_folder='cache', affiliation_conservative=False, num_processes=16,
                          use_proxy=False, pin_colorful=True, print_citing_affiliations=True,
                          use_flattened_authors=True, flattened_authors_path=flattened_authors_path)
