import sys
import os

# Add these debug prints
print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

# Add the parent directory of 'CitationMap' to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Add this debug print
print("Updated Python path:", sys.path)

from citation_map.citation_map import generate_citation_map

if __name__ == '__main__':
    # This is my Google Scholar ID. Replace this with your ID.
    # scholar_id = '3rDjnykAAAAJ'
    scholar_id = 'la-Mx-UAAAAJ'
    generate_citation_map(scholar_id, output_path='citation_map.html',
                          cache_folder='cache', affiliation_conservative=False, num_processes=16,  # Reduce to 1 process
                          use_proxy=False, pin_colorful=True, print_citing_affiliations=True)
