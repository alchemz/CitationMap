import csv
from collections import Counter
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

def analyze_citations_by_country(file_path):
    countries = []
    
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            country = row['country'].strip()
            if country:
                countries.append(country)

    country_counts = Counter(countries)
    
    # Separate countries with 4 or more citations and those with less
    main_countries = {k: v for k, v in country_counts.items() if v >= 4}
    small_countries = {k: v for k, v in country_counts.items() if v < 4}
    
    # Sort countries by count
    sorted_main_countries = sorted(main_countries.items(), key=lambda x: x[1], reverse=True)
    sorted_small_countries = sorted(small_countries.items(), key=lambda x: x[1], reverse=True)
    
    # Prepare data for sunburst chart
    labels = ["All Countries"] + [country for country, _ in sorted_main_countries]
    parents = [""] + ["All Countries" for _ in sorted_main_countries]
    values = [sum(main_countries.values())] + [count for _, count in sorted_main_countries]
    
    # Create subplots
    fig = make_subplots(rows=1, cols=2, specs=[[{'type':'domain'}, {'type':'table'}]],
                        column_widths=[0.7, 0.3],
                        subplot_titles=['Countries with 4 or More Citations', 
                                        'Countries with Less Than 4 Citations'])

    # Add sunburst chart
    fig.add_trace(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        hovertemplate='<b>%{label}</b><br>Citations: %{value}<br>Percentage: %{percentRoot:.1%}<extra></extra>',
        texttemplate='%{label}<br>%{percentRoot:.1%}<br>(%{value})',
        textfont=dict(size=10),
        name=""
    ), 1, 1)

    # Add table
    fig.add_trace(go.Table(
        header=dict(values=['Country', 'Citations'],
                    fill_color='rgba(0, 128, 128, 0.7)',
                    align='left',
                    font=dict(color='white', size=12)),
        cells=dict(values=[[country for country, _ in sorted_small_countries],
                           [count for _, count in sorted_small_countries]],
                   fill_color='rgba(240, 248, 255, 0.6)',
                   align='left',
                   font=dict(color='black', size=11))
    ), 1, 2)

    # Update layout
    fig.update_layout(
        # title_text="Distribution of Citing Authors by Country",
        title_font_size=24,
        title_x=0.5,
        title_y=0.95,
        showlegend=False,
        height=900,
        width=1400,
        annotations=[
            dict(text='Countries with 4 or More Citations', x=0.25, y=1.02, font_size=16, showarrow=False),
            dict(text='Countries with Less Than 4 Citations', x=0.85, y=1.02, font_size=16, showarrow=False)
        ],
        paper_bgcolor='rgba(240,248,255,0.7)',
        plot_bgcolor='rgba(240,248,255,0.7)',
        margin=dict(t=80, l=10, r=10, b=10)
    )

    # Update sunburst specific layout
    fig.update_layout(
        sunburstcolorway=["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52"],
    )

    # Save as static image
    output_path = os.path.join(os.path.dirname(file_path), "all_citing_authors_distribution.png")
    fig.write_image(output_path, scale=3, width=1400, height=900)
    print(f"Plot saved as: {output_path}")

    # Results
    total_papers = sum(country_counts.values())
    print(f"Total number of unique countries: {len(country_counts)}")
    print("\nDistribution of citing authors by country:")
    for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{country}: {count} ({count/total_papers*100:.1f}%)")

if __name__ == "__main__":
    file_path = "/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/citation_info_filled_sorted.csv"
    analyze_citations_by_country(file_path)