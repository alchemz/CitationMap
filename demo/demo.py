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

def combine_csv_files(folder_path):
    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    combined_df = pd.concat((pd.read_csv(f) for f in all_files), ignore_index=True)
    
    # Rename 'citing_authors' to 'citing_author_names' if it exists
    if 'citing_authors' in combined_df.columns:
        combined_df = combined_df.rename(columns={'citing_authors': 'citing_author_names'})
    
    combined_csv_path = os.path.join(folder_path, "combined_citations.csv")
    combined_df.to_csv(combined_csv_path, index=False)
    return combined_csv_path, 'citing_author_names' in combined_df.columns

if __name__ == '__main__':
    scholar_id = 'la-Mx-UAAAAJ'
    v2_cache_path = '/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/citations_DatasetEquity:_Are_All_Samples_Created_Equal?_In_T_checked_with_ids.csv'

    has_author_names = False
    if os.path.isdir(v2_cache_path):
        print(f"v2_cache_path is a directory. Combining all CSV files in {v2_cache_path}")
        v2_cache_path, has_author_names = combine_csv_files(v2_cache_path)
        print(f"Combined CSV file created at: {v2_cache_path}")
    elif os.path.isfile(v2_cache_path):
        # If it's a single file, check for 'citing_author_names' column
        df = pd.read_csv(v2_cache_path)
        if 'citing_authors' in df.columns:
            df = df.rename(columns={'citing_authors': 'citing_author_names'})
            df.to_csv(v2_cache_path, index=False)
            has_author_names = True
        elif 'citing_author_names' in df.columns:
            has_author_names = True
        print(f"Checked for 'citing_author_names' in {v2_cache_path}")
    else:
        print(f"Error: {v2_cache_path} is neither a file nor a directory.")
        sys.exit(1)

    generate_citation_map(scholar_id, output_path='citation_map.html',
                          cache_folder='cache', affiliation_conservative=False, num_processes=16,
                          use_proxy=False, pin_colorful=True, print_citing_affiliations=True,
                          use_v2_cache=True, v2_cache_path=v2_cache_path)
