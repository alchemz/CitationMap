# Copyright (c) 2024 Chen Liu
# All rights reserved.
import folium
import itertools
import pandas as pd
import os
import pickle
import pycountry
import re
import random
import time
import csv

from geopy.geocoders import Nominatim
from multiprocessing import Pool
from scholarly import scholarly, ProxyGenerator
from tqdm import tqdm
from typing import Any, Iterable, List, Tuple

from citation_map.scholarly_support import get_citing_author_ids_and_citing_papers, get_organization_name

def find_all_citing_authors(scholar_id: str, num_processes: int = 16) -> List[Tuple[str]]:
    '''
    Step 1. Find all publications of the given Google Scholar ID.
    Step 2. Find all citing authors.
    '''

    # Find Google Scholar Profile using Scholar ID.
    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=['publications'])
    publications = author['publications']
    print('Author profile found, with %d publications.\n' % len(publications))

    # Fetch metadata for all publications.
    if num_processes > 1 and isinstance(num_processes, int):
        with Pool(processes=num_processes) as pool:
            all_publications = list(tqdm(pool.imap(__fill_publication_metadata, publications),
                                         desc='Filling metadata for your %d publications' % len(publications),
                                         total=len(publications)))
    else:
        all_publications = []
        for pub in tqdm(publications,
                        desc='Filling metadata for your %d publications' % len(publications),
                        total=len(publications)):
            all_publications.append(__fill_publication_metadata(pub))

    # Convert all publications to Google Scholar publication IDs and paper titles.
    # This is fast and no parallel processing is needed.
    all_publication_info = []
    for pub in all_publications:
        pub_title = pub['bib']['title']
        if 'cites_id' in pub:
            for cites_id in pub['cites_id']:
                all_publication_info.append((cites_id, pub_title))
        else:
            # Include papers without cite IDs
            all_publication_info.append((None, pub_title))
        
        print(f"Publication: {pub['bib']['title']}")
        print(f"Number of citations: {pub['num_citations']}")
        print(f"Number of cites_id: {len(pub.get('cites_id', []))}")

    # Find all citing authors from all publications.
    if num_processes > 1 and isinstance(num_processes, int):
        with Pool(processes=num_processes) as pool:
            all_citing_author_paper_info_nested = list(tqdm(pool.imap(__citing_authors_and_papers_from_publication, all_publication_info),
                                                            desc='Finding citing authors and papers on your %d publications' % len(all_publication_info),
                                                            total=len(all_publication_info)))
    else:
        all_citing_author_paper_info_nested = []
        for pub in tqdm(all_publication_info,
                        desc='Finding citing authors and papers on your %d publications' % len(all_publication_info),
                        total=len(all_publication_info)):
            all_citing_author_paper_info_nested.append(__citing_authors_and_papers_from_publication(pub))
    all_citing_author_paper_tuple_list = list(itertools.chain(*all_citing_author_paper_info_nested))

    print("number of citing authors and papers: ", len(all_citing_author_paper_tuple_list))
    if all_citing_author_paper_tuple_list:
        print(all_citing_author_paper_tuple_list[0])
    else:
        print("No citing authors found.")
    return all_citing_author_paper_tuple_list

def find_all_citing_affiliations(all_citing_author_paper_tuple_list: List[Tuple[str, str, str, str]],
                                 num_processes: int = 16,
                                 affiliation_conservative: bool = False):
    '''
    Step 3. Find all citing affiliations.
    '''
    if affiliation_conservative:
        __affiliations_from_authors = __affiliations_from_authors_conservative
    else:
        __affiliations_from_authors = __affiliations_from_authors_aggressive

    # Find all citing institutions from all citing authors.
    if num_processes > 1 and isinstance(num_processes, int):
        with Pool(processes=num_processes) as pool:
            author_paper_affiliation_tuple_list = list(tqdm(pool.imap(__affiliations_from_authors, all_citing_author_paper_tuple_list),
                                                            desc='Finding citing affiliations from %d citing papers' % len(all_citing_author_paper_tuple_list),
                                                            total=len(all_citing_author_paper_tuple_list)))
    else:
        author_paper_affiliation_tuple_list = []
        for author_and_paper in tqdm(all_citing_author_paper_tuple_list,
                                     desc='Finding citing affiliations from %d citing papers' % len(all_citing_author_paper_tuple_list),
                                     total=len(all_citing_author_paper_tuple_list)):
            author_paper_affiliation_tuple_list.append(__affiliations_from_authors(author_and_paper))

    # Filter empty items and flatten the list.
    author_paper_affiliation_tuple_list = [item for sublist in author_paper_affiliation_tuple_list if sublist for item in sublist]
    return author_paper_affiliation_tuple_list

def clean_affiliation_names(author_paper_affiliation_tuple_list: List[Tuple[str]]) -> List[Tuple[str]]:
    '''
    Optional Step. Clean up the names of affiliations from the authors' affiliation tab on their Google Scholar profiles.
    NOTE: This logic is very naive. Please send an issue or pull request if you have any idea how to improve it.
    Currently we will not consider any paid service or tools that pose extra burden on the users, such as GPT API.
    '''
    cleaned_author_paper_affiliation_tuple_list = []
    for author_name, citing_paper_title, cited_paper_title, affiliation_string in author_paper_affiliation_tuple_list:
        # Use a regular expression to split the string by ';' or 'and'.
        substring_list = [part.strip() for part in re.split(r'[;]|\band\b', affiliation_string)]
        # Further split the substrings by ',' if the latter component is not a country.
        substring_list = __country_aware_comma_split(substring_list)

        for substring in substring_list:
            # Use a regular expression to remove anything before 'at', or '@'.
            cleaned_affiliation = re.sub(r'.*?\bat\b|.*?@', '', substring, flags=re.IGNORECASE).strip()
            # Use a regular expression to filter out strings that represent
            # a person's identity rather than affiliation.
            is_common_identity_string = re.search(
                re.compile(
                    r'\b(director|manager|chair|engineer|programmer|scientist|professor|lecturer|phd|ph\.d|postdoc|doctor|student|department of)\b',
                    re.IGNORECASE),
                cleaned_affiliation)
            if not is_common_identity_string:
                cleaned_author_paper_affiliation_tuple_list.append((author_name, citing_paper_title, cited_paper_title, cleaned_affiliation))
    return cleaned_author_paper_affiliation_tuple_list

def affiliation_text_to_geocode(author_paper_affiliation_tuple_list: List[Tuple[str]], max_attempts: int = 3) -> List[Tuple[str]]:
    '''
    Step 4: Convert affiliations in plain text to Geocode.
    '''
    coordinates_and_info = []
    # NOTE: According to the Nomatim Usage Policy (https://operations.osmfoundation.org/policies/nominatim/),
    # we are explicitly asked not to submit bulk requests on multiple threads.
    # Therefore, we will keep it to a loop instead of multiprocessing.
    geolocator = Nominatim(user_agent='citation_mapper')

    # Find unique affiliations and record their corresponding entries.
    affiliation_map = {}
    for entry_idx, (_, _, _, affiliation_name) in enumerate(author_paper_affiliation_tuple_list):
        if affiliation_name not in affiliation_map.keys():
            affiliation_map[affiliation_name] = [entry_idx]
        else:
            affiliation_map[affiliation_name].append(entry_idx)

    num_total_affiliations = len(affiliation_map)
    num_located_affiliations = 0
    for affiliation_name in tqdm(affiliation_map,
                                 desc='Finding geographic coordinates from %d unique citing affiliations in %d entries' % (
                                     len(affiliation_map), len(author_paper_affiliation_tuple_list)),
                                 total=len(affiliation_map)):
        for _ in range(max_attempts):
            try:
                geo_location = geolocator.geocode(affiliation_name)
                if geo_location:
                    # Get the full location metadata that includes county, city, state, country, etc.
                    location_metadata = geolocator.reverse(str(geo_location.latitude) + ',' + str(geo_location.longitude), language='en')
                    address = location_metadata.raw['address']
                    county, city, state, country = None, None, None, None
                    if 'county' in address:
                        county = address['county']
                    if 'city' in address:
                        city = address['city']
                    if 'state' in address:
                        state = address['state']
                    if 'country' in address:
                        country = address['country']

                    corresponding_entries = affiliation_map[affiliation_name]
                    for entry_idx in corresponding_entries:
                        author_name, citing_paper_title, cited_paper_title, affiliation_name = author_paper_affiliation_tuple_list[entry_idx]
                        coordinates_and_info.append((author_name, citing_paper_title, cited_paper_title, affiliation_name,
                                                     geo_location.latitude, geo_location.longitude,
                                                     county, city, state, country))
                    # This location is successfully recorded.
                    num_located_affiliations += 1
                    break
            except:
                continue
    print('\nConverted %d/%d affiliations to Geocodes.' % (num_located_affiliations, num_total_affiliations))
    coordinates_and_info = [item for item in coordinates_and_info if item is not None]  # Filter out empty entries.
    return coordinates_and_info

def create_map(coordinates_and_info: List[Tuple[str]], pin_colorful: bool = True):
    '''
    Step 5.1: Create the Citation World Map.

    For authors under the same affiliations, they will be displayed in the same pin.
    '''
    citation_map = folium.Map(location=[20, 0], zoom_start=2)

    # Find unique affiliations and record their corresponding entries.
    affiliation_map = {}
    for entry_idx, (_, _, _, affiliation_name, _, _, _, _, _, _) in enumerate(coordinates_and_info):
        if affiliation_name not in affiliation_map.keys():
            affiliation_map[affiliation_name] = [entry_idx]
        else:
            affiliation_map[affiliation_name].append(entry_idx)

    if pin_colorful:
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred',
                  'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
                  'darkpurple', 'pink', 'lightblue', 'lightgreen',
                  'gray', 'black', 'lightgray']
        for affiliation_name in affiliation_map:
            color = random.choice(colors)
            corresponding_entries = affiliation_map[affiliation_name]
            author_name_list = []
            for entry_idx in corresponding_entries:
                author_name, _, _, _, lat, lon, _, _, _, _  = coordinates_and_info[entry_idx]
                author_name_list.append(author_name)
            folium.Marker([lat, lon], popup='%s (%s)' % (affiliation_name, ' & '.join(author_name_list)),
                          icon=folium.Icon(color=color)).add_to(citation_map)
    else:
        for affiliation_name in affiliation_map:
            corresponding_entries = affiliation_map[affiliation_name]
            author_name_list = []
            for entry_idx in corresponding_entries:
                author_name, _, _, _, lat, lon, _, _, _, _  = coordinates_and_info[entry_idx]
                author_name_list.append(author_name)
            folium.Marker([lat, lon], popup='%s (%s)' % (affiliation_name, ' & '.join(author_name_list))).add_to(citation_map)
    return citation_map

def export_csv(coordinates_and_info: List[Tuple[str]], csv_output_path: str, all_citing_author_paper_tuple_list: List[Tuple[str]]) -> None:
    '''
    Step 5.2: Export csv files recording citation information.
    '''

    # Create DataFrame for authors with retrieved organization information
    citation_df = pd.DataFrame(coordinates_and_info,
                               columns=['citing author name', 'citing paper title', 'cited paper title',
                                        'affiliation', 'latitude', 'longitude',
                                        'county', 'city', 'state', 'country'])

    citation_df.to_csv(csv_output_path, index=False)
    print(f'\nCitation information for authors with retrieved organizations exported to {csv_output_path}')

    # Create DataFrame for all authors, including those without retrieved organization information
    all_authors_df = pd.DataFrame(all_citing_author_paper_tuple_list,
                                  columns=['citing_author_id', 'citing paper title', 'cited paper title'])
    
    # Explode the 'citing_author_id' column to create one row per author
    all_authors_df = all_authors_df.explode('citing_author_id')

    # Merge with the citation_df to add organization information where available
    merged_df = pd.merge(all_authors_df, citation_df, 
                         left_on=['citing_author_id', 'citing paper title', 'cited paper title'],
                         right_on=['citing author name', 'citing paper title', 'cited paper title'],
                         how='left')

    # Fill NaN values with 'NA' for organization-related columns
    org_columns = ['affiliation', 'latitude', 'longitude', 'county', 'city', 'state', 'country']
    merged_df[org_columns] = merged_df[org_columns].fillna('NA')

    # Rename 'citing_author_id' to 'author_name' if it's not already present
    if 'author_name' not in merged_df.columns:
        merged_df = merged_df.rename(columns={'citing_author_id': 'author_name'})

    # Reorder columns
    columns = ['author_name', 'citing paper title', 'cited paper title', 'affiliation', 
               'latitude', 'longitude', 'county', 'city', 'state', 'country']
    merged_df = merged_df[columns]

    # Save the merged DataFrame to a new CSV file
    all_authors_csv_path = csv_output_path.replace('.csv', '_all_authors.csv')
    merged_df.to_csv(all_authors_csv_path, index=False)
    print(f'Citation information for all authors exported to {all_authors_csv_path}')

def __fill_publication_metadata(pub):
    time.sleep(random.uniform(10, 15))  # Increased delay
    try:
        filled_pub = scholarly.fill(pub)
        print(f"Title: {filled_pub['bib']['title']}")
        print(f"Reported citations: {filled_pub['num_citations']}")
        if 'cites_id' in filled_pub:
            print(f"Number of cites_id: {len(filled_pub['cites_id'])}")
        else:
            print("No cites_id found")
        return filled_pub
    except Exception as e:
        print(f"Error filling publication metadata: {e}")
        return pub

def __citing_authors_and_papers_from_publication(cites_id_and_cited_paper: Tuple[str, str]):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            cites_id, cited_paper_title = cites_id_and_cited_paper
            if cites_id is None:
                # For papers without cite IDs, return an empty list of citing authors
                return [([], "", cited_paper_title)]
            citing_paper_search_url = 'https://scholar.google.com/scholar?hl=en&cites=' + cites_id
            print(f"\n\n####Citing paper search URL: {citing_paper_search_url}")
            citing_authors_and_citing_papers = get_citing_author_ids_and_citing_papers(citing_paper_search_url)
            citing_author_paper_info = []
            for citing_author_ids, citing_paper_title in citing_authors_and_citing_papers:
                # If citing_author_ids is a string, wrap it in a list
                if isinstance(citing_author_ids, str):
                    citing_author_ids = [citing_author_ids]
                citing_author_paper_info.append((citing_author_ids, citing_paper_title, cited_paper_title))
            return citing_author_paper_info
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(10, 15))
            else:
                print(f"Failed after {max_retries} attempts")
    return []

def __affiliations_from_authors_conservative(citing_author_paper_info: Tuple[List[str], str, str, str]):
    print("citing_author_paper_info", citing_author_paper_info)
    citing_author_ids, citing_paper_title, cited_paper_title, citing_author_names = citing_author_paper_info
    affiliations = []
    if isinstance(citing_author_ids, str):
        citing_author_ids = [citing_author_ids]
    for citing_author_id, citing_author_name in zip(citing_author_ids, citing_author_names.split(', ')):
        if citing_author_id.lower() == 'na':
            print(f"Skipping author ID: NA")
            continue
        max_retries = 3
        for attempt in range(max_retries):
            try:
                time.sleep(random.uniform(5, 10))  # Increased delay
                print(f"Searching for author with ID: {citing_author_id}")
                citing_author = scholarly.search_author_id(citing_author_id)
                if citing_author is None:
                    print(f"[Warning!] Author with ID {citing_author_id} not found on attempt {attempt + 1}.")
                    if attempt == max_retries - 1:
                        print(f"[Error] Failed to find author with ID {citing_author_id} after {max_retries} attempts.")
                    continue
                
                print(f"Author found: {citing_author.get('name', 'Name not available')}")
                author_name = citing_author_name or citing_author.get('name', 'Name not available')
                
                if 'organization' in citing_author:
                    try:
                        author_organization = get_organization_name(citing_author['organization'])
                        affiliations.append((author_name, citing_paper_title, cited_paper_title, author_organization))
                    except Exception as e:
                        print(f'[Warning!] Error processing organization for author {author_name}: {e}')
                else:
                    print(f"No organization information found for author {author_name}")
                    if 'affiliation' in citing_author:
                        affiliation_parts = citing_author['affiliation'].split(',')
                        if len(affiliation_parts) > 1:
                            author_organization = affiliation_parts[-1].strip()
                        else:
                            author_organization = citing_author['affiliation'].strip()
                        print(f"Extracted organization: {author_organization}")
                        affiliations.append((author_name, citing_paper_title, cited_paper_title, author_organization))
                    else:
                        print(f"No affiliation information found for author {author_name}")
                
                break  # Successfully processed this author, move to the next
            except Exception as e:
                print(f'[Warning!] Error searching for author with ID {citing_author_id} on attempt {attempt + 1}: {e}')
                print(f'Exception type: {type(e).__name__}')
                print(f'Exception args: {e.args}')
                if attempt == max_retries - 1:
                    print(f"[Error] Failed to process author with ID {citing_author_id} after {max_retries} attempts.")
    return affiliations

def __affiliations_from_authors_aggressive(citing_author_paper_info: Tuple[List[str], str, str, str]):
    citing_author_ids, citing_paper_title, cited_paper_title, citing_author_names = citing_author_paper_info
    affiliations = []
    if isinstance(citing_author_ids, str):
        citing_author_ids = [citing_author_ids]
    for citing_author_id, citing_author_name in zip(citing_author_ids, citing_author_names.split(', ')):
        if citing_author_id.lower() == 'na':
            print(f"Skipping author ID: NA")
            continue
        max_retries = 3
        for attempt in range(max_retries):
            try:
                time.sleep(random.uniform(5, 10))  # Increased delay
                print(f"Searching for author with ID: {citing_author_id}")
                citing_author = scholarly.search_author_id(citing_author_id)
                if citing_author is None:
                    print(f"[Warning!] Author with ID {citing_author_id} not found on attempt {attempt + 1}.")
                    if attempt == max_retries - 1:
                        print(f"[Error] Failed to find author with ID {citing_author_id} after {max_retries} attempts.")
                    continue
                
                print(f"Author found: {citing_author.get('name', 'Name not available')}")
                author_name = citing_author_name or citing_author.get('name', 'Name not available')
                
                if 'affiliation' in citing_author:
                    affiliation_parts = citing_author['affiliation'].split(',')
                    if len(affiliation_parts) > 1:
                        author_organization = affiliation_parts[-1].strip()
                    else:
                        author_organization = citing_author['affiliation'].strip()
                    print(f"Extracted organization: {author_organization}")
                    affiliations.append((author_name, citing_paper_title, cited_paper_title, author_organization))
                else:
                    print(f"No affiliation information found for author {author_name}")
                
                break  # Successfully processed this author, move to the next
            except Exception as e:
                print(f'[Warning!] Error searching for author with ID {citing_author_id} on attempt {attempt + 1}: {e}')
                print(f'Exception type: {type(e).__name__}')
                print(f'Exception args: {e.args}')
                if attempt == max_retries - 1:
                    print(f"[Error] Failed to process author with ID {citing_author_id} after {max_retries} attempts.")
    return affiliations

def __country_aware_comma_split(string_list: List[str]) -> List[str]:
    comma_split_list = []

    for part in string_list:
        # Split the strings by comma.
        # NOTE: The non-English comma is entered intentionally.
        sub_parts = [sub_part.strip() for sub_part in re.split(r'[,，]', part)]
        sub_parts_iter = iter(sub_parts)

        # Merge the split strings if the latter component is a country name.
        for sub_part in sub_parts_iter:
            if __iscountry(sub_part):
                continue  # Skip country names if they appear as the first sub_part.
            next_part = next(sub_parts_iter, None)
            if __iscountry(next_part):
                comma_split_list.append(f"{sub_part}, {next_part}")
            else:
                comma_split_list.append(sub_part)
                if next_part:
                    comma_split_list.append(next_part)
    return comma_split_list

def __iscountry(string: str) -> bool:
    try:
        pycountry.countries.lookup(string)
        return True
    except LookupError:
        return False

def __print_author_and_affiliation(author_paper_affiliation_tuple_list: List[Tuple[str]]) -> None:
    __author_affiliation_tuple_list = []
    for author_name, _, _, affiliation_name in sorted(author_paper_affiliation_tuple_list):
        __author_affiliation_tuple_list.append((author_name, affiliation_name))

    # Take unique tuples.
    # __author_affiliation_tuple_list = list(set(__author_affiliation_tuple_list))
    for author_name, affiliation_name in sorted(__author_affiliation_tuple_list):
        print('Author: %s. Affiliation: %s.' % (author_name, affiliation_name))
    print('')
    return


def save_cache(data: List[Tuple[str, str, str]], fpath: str) -> None:
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    with open(fpath, "w", newline='', encoding='utf-8') as fd:
        writer = csv.writer(fd)
        writer.writerow(['source_title', 'citedby_url', 'citing_year', 'citing_title', 'citing_authors', 'citing_author_id', 'citing_url'])
        for item in data:
            author_ids, citing_paper_title, cited_paper_title = item
            if isinstance(author_ids, list):
                author_ids = ','.join(author_ids) if author_ids else "NA"
            elif author_ids is None:
                author_ids = "NA"
            # Note: We're leaving some fields blank as we don't have this information in our current data structure
            writer.writerow([cited_paper_title, '', '', citing_paper_title, '', author_ids, ''])

def load_cache(fpath: str) -> List[Tuple[str, str, str]]:
    data = []
    with open(fpath, "r", encoding='utf-8') as fd:
        reader = csv.reader(fd)
        next(reader)  # Skip header
        for row in reader:
            cited_paper_title, author_ids, citing_paper_title = row
            if author_ids == "NA":
                author_ids = []
            else:
                author_ids = author_ids.split(',')
            data.append((author_ids, citing_paper_title, cited_paper_title))
    return data

def load_cache_v2(fpath: str) -> List[Tuple[str, str, str, str]]:
    data = []
    df = pd.read_csv(fpath)
    for _, row in df.iterrows():
        cited_paper_title = row['source_title']
        author_ids = row['citing_author_id'].split(',') if pd.notna(row['citing_author_id']) else []
        author_ids = [aid.strip() for aid in author_ids if aid.strip()]  # Remove empty strings and whitespace
        citing_paper_title = row['citing_title']
        citing_author_names = row['citing_author_names'] if 'citing_author_names' in row else ''
        if author_ids:  # Only add to data if there are valid author IDs
            data.append((author_ids, citing_paper_title, cited_paper_title, citing_author_names))
    return data

def generate_citation_map(scholar_id: str,
                          output_path: str = 'citation_map.html',
                          csv_output_path: str = 'citation_info.csv',
                          cache_folder: str = 'cache',
                          affiliation_conservative: bool = True,
                          num_processes: int = 16,
                          use_proxy: bool = False,
                          pin_colorful: bool = True,
                          print_citing_affiliations: bool = True,
                          use_v2_cache: bool = False,
                          v2_cache_path: str = None,
                          has_author_names: bool = False):
    '''
    Google Scholar Citation World Map.

    Parameters
    ----
    scholar_id: str
        Your Google Scholar ID.
    output_path: str
        (default is 'citation_map.html')
        The path to the output HTML file.
    csv_output_path: str
        (default is 'citation_info.csv')
        The path to the output csv file.
    cache_folder: str
        (default is 'cache')
        The folder to save intermediate results, after finding (author, paper) but before finding the affiliations.
        This is because the user might want to try the aggressive vs. conservative approach.
        Set to None if you do not want caching.
    affiliation_conservative: bool
        (default is False)
        If true, we will use a more conservative approach to identify affiliations.
        If false, we will use a more aggressive approach to identify affiliations.
    num_processes: int
        (default is 16)
        Number of processes for parallel processing.
    use_proxy: bool
        (default is False)
        If true, we will use a scholarly proxy.
        It is necessary for some environments to avoid blocks, but it usually makes things slower.
    pin_colorful: bool
        (default is True)
        If true, the location pins will have a variety of colors.
        Otherwise, it will only have one color.
    print_citing_affiliations: bool
        (default is True)
        If true, print the list of citing affiliations (affiliations of citing authors).
    use_v2_cache: bool
        (default is False)
        If true, use the v2 cache loading function.
    v2_cache_path: str
        (default is None)
        The path to the v2 cache file.
    has_author_names: bool
        (default is False)
        If true, the v2 cache file contains author names.
    '''

    if use_proxy:
        pg = ProxyGenerator()
        pg.FreeProxies()
        scholarly.use_proxy(pg)
        print('Using proxy.')

    if cache_folder is not None:
        cache_path = os.path.join(cache_folder, scholar_id, 'all_citing_author_paper_tuple_list.csv')
    else:
        cache_path = None

    if use_v2_cache and v2_cache_path:
        print('Loading data from v2 cache.\n')
        all_citing_author_paper_tuple_list = load_cache_v2(v2_cache_path)
        print(f'Loaded from v2 cache: {v2_cache_path}.\n')
        print(f'A total of {len(all_citing_author_paper_tuple_list)} citing authors loaded.\n')
    
    # ... (rest of the function remains the same)

    # Modify the find_all_citing_affiliations function call
    author_paper_affiliation_tuple_list = find_all_citing_affiliations(all_citing_author_paper_tuple_list,
                                                                       num_processes=num_processes,
                                                                       affiliation_conservative=affiliation_conservative)

    # ... (rest of the function remains the same)


if __name__ == '__main__':
    # Replace this with your Google Scholar ID.
    scholar_id = '3rDjnykAAAAJ'
    generate_citation_map(scholar_id, output_path='citation_map.html', csv_output_path='citation_info.csv',
                          cache_folder='cache', affiliation_conservative=True, num_processes=16,
                          use_proxy=False, pin_colorful=True, print_citing_affiliations=True,
                          use_v2_cache=False, v2_cache_path=None, has_author_names=False)
