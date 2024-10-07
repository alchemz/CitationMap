import csv
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from tqdm import tqdm
import time
import random
import os

def get_coordinates(geolocator, location):
    max_attempts = 3
    for _ in range(max_attempts):
        try:
            geo_location = geolocator.geocode(location)
            if geo_location:
                # Get the full location metadata that includes county, city, state, country, etc.
                location_metadata = geolocator.reverse(f"{geo_location.latitude},{geo_location.longitude}", language='en')
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
                return geo_location, county, city, state, country
        except (GeocoderTimedOut, GeocoderServiceError):
            time.sleep(random.uniform(1, 3))
    return None, None, None, None, None

def update_citation_info_with_location(citation_info_file):
    geolocator = Nominatim(user_agent="citation_mapper")
    updated_citations = []

    # Read the citation info file
    with open(citation_info_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in tqdm(reader, desc="Updating location information"):
            affiliation = row['affiliation']
            
            if affiliation and affiliation.strip() != "":
                location_info, county, city, state, country = get_coordinates(geolocator, affiliation)
                
                row['county'] = county or row.get('county', 'N/A')
                row['city'] = city or row.get('city', 'N/A')
                row['state'] = state or row.get('state', 'N/A')
                row['country'] = country or row.get('country', 'N/A')
                
                if location_info:
                    row['latitude'] = location_info.latitude
                    row['longitude'] = location_info.longitude
                
                # print(f"\nAffiliation: {affiliation}")
                # print(f"Updated City: {row['city']}")
                # print(f"Updated State: {row['state']}")
                # print(f"Updated Country: {row['country']}")
                # print("---")
            else:
                row['county'] = row.get('county', 'N/A')
                row['city'] = row.get('city', 'N/A')
                row['state'] = row.get('state', 'N/A')
                row['country'] = row.get('country', 'N/A')
            
            updated_citations.append(row)
            time.sleep(random.uniform(0.5, 1.5))  # Add a small delay to avoid overwhelming the geocoding service

    # Create a new file name
    file_name, file_extension = os.path.splitext(citation_info_file)
    new_file = f"{file_name}_with_updated_location{file_extension}"

    # Write the updated information to the new file
    with open(new_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_citations)

    print(f"Updated citation info with location information saved to: {new_file}")
    return new_file

def draw_citation_map(citation_info_file, output_file):
    # Initialize geolocator
    geolocator = Nominatim(user_agent="citation_mapper")

    # Read the citation info file
    citations = []
    with open(citation_info_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            citations.append(row)

    # Create a map centered on the world
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Define colors for pins
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred',
              'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
              'darkpurple', 'pink', 'lightblue', 'lightgreen',
              'gray', 'black', 'lightgray']

    # Create a dictionary to store affiliations and their corresponding entries
    affiliation_map = {}

    # Process each citation and add markers to the map
    for citation in tqdm(citations, desc="Processing citations"):
        affiliation = citation['affiliation']
        
        # Skip if no affiliation information
        if not affiliation or affiliation.strip() == "":
            continue

        # Get coordinates and location info
        location_info, county, city, state, country = get_coordinates(geolocator, affiliation)
        
        # Print affiliation and retrieved location information
        # print(f"Affiliation: {affiliation}")
        # print(f"Retrieved City: {city or 'N/A'}")
        # print(f"Retrieved State: {state or 'N/A'}")
        # print(f"Retrieved Country: {country or 'N/A'}")
        # print("---")

        if location_info:
            # Add the citation to the affiliation_map
            if affiliation not in affiliation_map:
                affiliation_map[affiliation] = []
            affiliation_map[affiliation].append(citation)

    # Add markers for each affiliation
    for affiliation, citations in affiliation_map.items():
        color = random.choice(colors)
        location_info, county, city, state, country = get_coordinates(geolocator, affiliation)
        
        if location_info:
            # Create popup text
            popup_text = f"<b>Affiliation:</b> {affiliation}<br>"
            popup_text += f"<b>City:</b> {city or 'N/A'}<br>"
            popup_text += f"<b>State:</b> {state or 'N/A'}<br>"
            popup_text += f"<b>Country:</b> {country or 'N/A'}<br><br>"
            
            for citation in citations:
                popup_text += f"<b>Author:</b> {citation['citing author name']}<br>"
                popup_text += f"<b>Citing Paper:</b> {citation['citing paper title']}<br>"
                popup_text += f"<b>Cited Paper:</b> {citation['cited paper title']}<br><br>"

            # Add marker to the map
            folium.Marker(
                location=[location_info.latitude, location_info.longitude],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color=color)
            ).add_to(m)

        # Add a small delay to avoid overwhelming the geocoding service
        time.sleep(random.uniform(0.5, 1.5))

    # Save the map
    m.save(output_file)
    print(f"Map saved to {output_file}")

if __name__ == "__main__":
    citation_info_file = '/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/citation_info_updated.csv'
    output_file = '/Users/lilyzhang/Desktop/Demo/CitationMap/citation_map.html'
    
    # Update citation info with location information
    updated_citation_info_file = update_citation_info_with_location(citation_info_file)
    
    # Draw the map using the updated citation info file
    draw_citation_map(updated_citation_info_file, output_file)