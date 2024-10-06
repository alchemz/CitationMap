import csv
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from tqdm import tqdm
import time
import random

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

    # Process each citation and add markers to the map
    for citation in tqdm(citations, desc="Processing citations"):
        affiliation = citation['affiliation']
        
        # Skip if no affiliation information
        if not affiliation or affiliation.strip() == "":
            continue

        # Get coordinates and location info
        location_info, county, city, state, country = get_coordinates(geolocator, affiliation)
        
        # Print affiliation and retrieved location information
        print(f"Affiliation: {affiliation}")
        print(f"Retrieved City: {city or 'N/A'}")
        print(f"Retrieved State: {state or 'N/A'}")
        print(f"Retrieved Country: {country or 'N/A'}")
        print("---")

        if location_info:
            # Create popup text
            popup_text = f"""
            <b>Author:</b> {citation['citing author name']}<br>
            <b>Affiliation:</b> {affiliation}<br>
            <b>Citing Paper:</b> {citation['citing paper title']}<br>
            <b>Cited Paper:</b> {citation['cited paper title']}<br>
            <b>City:</b> {city or 'N/A'}<br>
            <b>State:</b> {state or 'N/A'}<br>
            <b>Country:</b> {country or 'N/A'}
            """

            # Add marker to the map
            folium.Marker(
                location=[location_info.latitude, location_info.longitude],
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(m)

        # Add a small delay to avoid overwhelming the geocoding service
        time.sleep(random.uniform(0.5, 1.5))

    # Save the map
    m.save(output_file)
    print(f"Map saved to {output_file}")

if __name__ == "__main__":
    # citation_info_file = '/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/citation_info_updated.csv'
    citation_info_file = '/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/citation_info_updated_test.csv'
    output_file = '/Users/lilyzhang/Desktop/Demo/CitationMap/citation_map.html'
    draw_citation_map(citation_info_file, output_file)