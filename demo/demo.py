import sys
import os
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Add the parent directory of 'CitationMap' to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from citation_map.citation_map import generate_citation_map

if __name__ == '__main__':
    scholar_id = 'la-Mx-UAAAAJ'
    v2_cache_path = '/Users/lilyzhang/Desktop/Demo/citations_la-Mx-UAAAAJ/citations_SIMBAR:_Single_Image-Based_Scene_Relighting_For_Ef.csv'
    
    generate_citation_map(scholar_id, output_path='citation_map.html',
                          cache_folder='cache', affiliation_conservative=False, num_processes=16,
                          use_proxy=False, pin_colorful=True, print_citing_affiliations=True,
                          use_v2_cache=True, v2_cache_path=v2_cache_path)
