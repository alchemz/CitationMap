import pandas as pd

def join_citation_info(citation_info_path, flattened_authors_path, output_path):
    # Read the CSV files
    citation_info = pd.read_csv(citation_info_path)
    flattened_authors = pd.read_csv(flattened_authors_path)

    # Rename columns to ensure consistency
    citation_info = citation_info.rename(columns={
        'citing author name': 'citing_author_name',
        'citing paper title': 'citing_paper',
        'cited paper title': 'source_paper'
    })

    # Merge the dataframes
    merged_df = pd.merge(
        flattened_authors,
        citation_info,
        on=['citing_author_name', 'citing_paper', 'source_paper'],
        how='left'
    )

    # Fill NaN values in the newly added columns with 'NA'
    columns_to_fill = ['affiliation', 'latitude', 'longitude', 'county', 'city', 'state', 'country']
    merged_df[columns_to_fill] = merged_df[columns_to_fill].fillna('NA')

    # Reorder columns
    column_order = [
        'citing_author_name', 'citing_author_id', 'match_status', 'citing_year',
        'citing_paper', 'source_paper', 'citedby_url', 'citing_url',
        'affiliation', 'latitude', 'longitude', 'county', 'city', 'state', 'country'
    ]
    merged_df = merged_df[column_order]

    # Save the merged dataframe
    merged_df.to_csv(output_path, index=False)
    print(f"Merged file saved to: {output_path}")

    # Print some statistics
    total_authors = len(merged_df)
    authors_with_affiliation = (merged_df['affiliation'] != 'NA').sum()
    print(f"Total authors: {total_authors}")
    print(f"Authors with affiliation: {authors_with_affiliation}")
    print(f"Percentage of authors with affiliation: {authors_with_affiliation / total_authors * 100:.2f}%")

if __name__ == "__main__":
    citation_info_path = '/Users/lilyzhang/Desktop/Demo/CitationMap/citation_info.csv'
    flattened_authors_path = '/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/flattened_authors.csv'
    output_path = '/Users/lilyzhang/Desktop/Demo/CitationMap/status_checked/merged_citation_info.csv'

    join_citation_info(citation_info_path, flattened_authors_path, output_path)