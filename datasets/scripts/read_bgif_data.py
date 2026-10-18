import pandas as pd

def main():
    num_datasets = 34
    datasets_folder_path = "<datasets>/gbif-plants-raw/data/"
    datasets_prefix = "train-"
    datasets_postfix = f"-of-000{num_datasets}.parquet"

    output_path = "<datasets>/iNaturalist_species_ids.parquet"

    new_df = pd.DataFrame()

    for i in range(num_datasets):
        dataset_path = f"{datasets_folder_path}{datasets_prefix}{i:05d}{datasets_postfix}"
        df = pd.read_parquet(dataset_path)
        new_df = pd.concat([new_df, df['species_id']])

    new_df = new_df.dropna()
    new_df['species_id'] = new_df['species_id'].astype(int)

    print(new_df.head())
    print(new_df.size)

    new_df.to_parquet(output_path)


if __name__ == "__main__":
    main()