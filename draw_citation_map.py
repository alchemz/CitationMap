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
        total_rows = sum(1 for row in reader)  # Count total number of rows
        f.seek(0)  # Reset file pointer
        reader = csv.DictReader(f)  # Recreate reader
        
        for row in tqdm(reader, total=total_rows, desc="Updating location information"):
            affiliation = row['affiliation']
            
            # Check if latitude is already present
            if 'latitude' in row and row['latitude'] and row['latitude'] != 'N/A':
                # If latitude is present, keep existing location information
                updated_citations.append(row)
            elif affiliation and affiliation.strip() != "":
                location_info, county, city, state, country = get_coordinates(geolocator, affiliation)
                
                row['county'] = county or row.get('county', 'N/A')
                row['city'] = city or row.get('city', 'N/A')
                row['state'] = state or row.get('state', 'N/A')
                row['country'] = country or row.get('country', 'N/A')
                
                if location_info:
                    row['latitude'] = location_info.latitude
                    row['longitude'] = location_info.longitude
                else:
                    row['latitude'] = row.get('latitude', 'N/A')
                    row['longitude'] = row.get('longitude', 'N/A')
                
                updated_citations.append(row)
                time.sleep(random.uniform(0.5, 1.5))  # Add a small delay to avoid overwhelming the geocoding service
            else:
                row['county'] = row.get('county', 'N/A')
                row['city'] = row.get('city', 'N/A')
                row['state'] = row.get('state', 'N/A')
                row['country'] = row.get('country', 'N/A')
                row['latitude'] = row.get('latitude', 'N/A')
                row['longitude'] = row.get('longitude', 'N/A')
                updated_citations.append(row)

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

    # Process each citation and add to affiliation_map
    for citation in tqdm(citations, desc="Processing citations"):
        affiliation = citation['affiliation']
        latitude = citation.get('latitude', '')
        longitude = citation.get('longitude', '')
        
        if latitude and longitude and latitude != 'N/A' and longitude != 'N/A':
            try:
                float(latitude)
                float(longitude)
                if affiliation not in affiliation_map:
                    affiliation_map[affiliation] = []
                affiliation_map[affiliation].append(citation)
            except ValueError:
                print(f"Invalid latitude or longitude for affiliation: {affiliation}")

    # Add markers for each affiliation
    for affiliation, citations in tqdm(affiliation_map.items(), desc="Adding markers to map"):
        color = random.choice(colors)
        
        # Use the first citation's lat/long for the marker
        try:
            latitude = float(citations[0]['latitude'])
            longitude = float(citations[0]['longitude'])
        except ValueError:
            print(f"Skipping affiliation due to invalid coordinates: {affiliation}")
            continue
        
        # Create popup text
        popup_text = f"<b>Affiliation:</b> {affiliation}<br>"
        popup_text += f"<b>City:</b> {citations[0].get('city', 'N/A')}<br>"
        popup_text += f"<b>State:</b> {citations[0].get('state', 'N/A')}<br>"
        popup_text += f"<b>Country:</b> {citations[0].get('country', 'N/A')}<br><br>"
        
        for citation in citations:
            popup_text += f"<b>Author:</b> {citation.get('citing author name', 'N/A')}<br>"
            popup_text += f"<b>Citing Paper:</b> {citation.get('citing paper title', 'N/A')}<br>"
            popup_text += f"<b>Cited Paper:</b> {citation.get('cited paper title', 'N/A')}<br><br>"

        # Add marker to the map
        folium.Marker(
            location=[latitude, longitude],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color=color)
        ).add_to(m)

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