import csv
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from tqdm import tqdm
import time
import random
import os
import pycountry_convert as pc
from folium.plugins import MarkerCluster

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

def get_continent(country_name):
    try:
        country_alpha2 = pc.country_name_to_country_alpha2(country_name)
        country_continent_code = pc.country_alpha2_to_continent_code(country_alpha2)
        continent_name = pc.convert_continent_code_to_continent_name(country_continent_code)
        return continent_name
    except:
        return "Unknown"

def get_citation_count(x):
    try:
        return int(x.get('citations', 0))
    except ValueError:
        return 0  # Return 0 for 'NA' or any non-numeric value

def draw_citation_map(citation_info_file, output_file):
    # Read the citation info file
    citations = []
    with open(citation_info_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            citations.append(row)

    # Create a map centered on the world
    m = folium.Map(location=[20, 0], zoom_start=2, tiles='CartoDB positron')

    # Define color schemes for each continent
    continent_colors = {
        'Africa': '#CD5C5C',
        'Europe': '#006400',
        'Asia': '#8B008B',
        'North America': '#0000CD',
        'South America': '#8B4513',
        'Oceania': '#008080',
        'Antarctica': '#708090',
        'Unknown': '#2F4F4F'
    }

    # Create a MarkerCluster with custom options
    marker_cluster = MarkerCluster(
        options={
            'maxClusterRadius': 15,  # Reduce cluster radius
            'disableClusteringAtZoom': 4,  # Disable clustering at higher zoom levels
            'spiderfyOnMaxZoom': False,  # Disable spiderfy effect
            'showCoverageOnHover': False,  # Don't show bounds of clusters on hover
        }
    ).add_to(m)

    # Dictionary to store the number of authors at each location
    location_count = {}

    # Process each citation and add markers
    for citation in tqdm(citations, desc="Adding markers to map"):
        latitude = citation.get('latitude', '')
        longitude = citation.get('longitude', '')
        country = citation.get('country', 'Unknown')
        author = citation.get('citing author name', 'Unknown')
        affiliation = citation.get('affiliation', 'Unknown')
        citation_count = get_citation_count(citation)
        
        if latitude and longitude and latitude != 'N/A' and longitude != 'N/A':
            try:
                latitude = float(latitude)
                longitude = float(longitude)
                
                # Add a larger random offset to spread out markers from the same location
                location_key = f"{latitude:.2f},{longitude:.2f}"  # Reduced precision for grouping
                if location_key in location_count:
                    location_count[location_key] += 1
                    offset = min(location_count[location_key], 20) * 0.05  # Increased spread
                else:
                    location_count[location_key] = 1
                    offset = 0

                latitude += random.uniform(-offset, offset)
                longitude += random.uniform(-offset, offset)
                
                continent = get_continent(country)
                color = continent_colors.get(continent, continent_colors['Unknown'])
                
                # Create popup text
                popup_text = f"<div style='font-family: Arial, sans-serif;'>"
                popup_text += f"<h3 style='color: #333;'>{author}</h3>"
                popup_text += f"<p><b>Affiliation:</b> {affiliation}<br>"
                popup_text += f"<b>City:</b> {citation.get('city', 'N/A')}<br>"
                popup_text += f"<b>State:</b> {citation.get('state', 'N/A')}<br>"
                popup_text += f"<b>Country:</b> {country}<br>"
                popup_text += f"<b>Citations:</b> {citation_count}</p>"
                popup_text += "</div>"
                
                # Add marker to the cluster
                folium.CircleMarker(
                    location=[latitude, longitude],
                    radius=6,
                    popup=folium.Popup(popup_text, max_width=300),
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7
                ).add_to(marker_cluster)

            except ValueError:
                print(f"Invalid latitude or longitude for author: {author}")

    # Add a custom legend
    legend_html = '''
    <div style="
        position: fixed; 
        top: 10px;
        left: 50px;
        width: 90%;
        height: 40px;
        z-index: 9999; 
        font-size: 14px; 
        background-color: rgba(255, 255, 255, 0.8);
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 0 15px rgba(0,0,0,0.2);">
        <div style="float: left; margin-right: 20px;"><strong>Legend:</strong></div>
        <div style="float: left; margin-right: 15px;"><i class="fa fa-circle" style="color:#CD5C5C"></i> Africa</div>
        <div style="float: left; margin-right: 15px;"><i class="fa fa-circle" style="color:#006400"></i> Europe</div>
        <div style="float: left; margin-right: 15px;"><i class="fa fa-circle" style="color:#8B008B"></i> Asia</div>
        <div style="float: left; margin-right: 15px;"><i class="fa fa-circle" style="color:#0000CD"></i> N. America</div>
        <div style="float: left; margin-right: 15px;"><i class="fa fa-circle" style="color:#8B4513"></i> S. America</div>
        <div style="float: left; margin-right: 15px;"><i class="fa fa-circle" style="color:#008080"></i> Oceania</div>
        <div style="float: left; margin-right: 15px;"><i class="fa fa-circle" style="color:#708090"></i> Antarctica</div>
        <div style="float: left; margin-right: 15px;"><i class="fa fa-circle" style="color:#2F4F4F"></i> Unknown</div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Save the map
    m.save(output_file)
    print(f"Map saved to {output_file}")

if __name__ == "__main__":
    # citation_info_file = '/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/citation_info_updated.csv'
    citation_info_file = '/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/citation_info_filled_sorted.csv'
    output_file = '/Users/lilyzhang/Desktop/Demo/CitationMap/citation_map.html'
    
    # Update citation info with location information
    updated_citation_info_file = update_citation_info_with_location(citation_info_file)
    
    # Draw the map using the updated citation info file
    draw_citation_map(updated_citation_info_file, output_file)