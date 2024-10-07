import csv
from collections import Counter
import matplotlib.pyplot as plt

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
    
    # Prepare data for pie chart
    labels = [country for country, _ in sorted_main_countries]
    sizes = [count for _, count in sorted_main_countries]
    
    # Plotting
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10), gridspec_kw={'width_ratios': [3, 1]})
    
    # Pie chart
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct*total/100.0))
            return f'{pct:.1f}%\n({val:d})'
        return my_autopct

    ax1.pie(sizes, labels=labels, autopct=make_autopct(sizes), startangle=90, pctdistance=0.85)
    ax1.set_title('Distribution of Citing Authors by Country (4 or more citations)')
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    # Add a circle at the center to make it a donut chart
    center_circle = plt.Circle((0,0), 0.70, fc='white')
    ax1.add_artist(center_circle)
    
    # Table for countries with less than 4 citations
    table_data = [['Country', 'Citations']] + [[country, count] for country, count in sorted_small_countries]
    table = ax2.table(cellText=table_data, loc='center', cellLoc='center', colWidths=[0.6, 0.4])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    ax2.axis('off')
    ax2.set_title('Countries with Less Than 4 Citations')
    
    plt.tight_layout()
    plt.savefig('citing_authors_distribution_with_table.png', dpi=300, bbox_inches='tight')
    plt.close()

    # Results
    total_papers = sum(country_counts.values())
    print(f"Total number of unique countries: {len(country_counts)}")
    print("\nDistribution of citing authors by country:")
    for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{country}: {count} ({count/total_papers*100:.1f}%)")

if __name__ == "__main__":
    file_path = "/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/citation_info_filled_sorted.csv"
    analyze_citations_by_country(file_path)