import os

""" Useful script to clean all .csvs from data folders - useful to 'start from scratch' when processing data"""

if __name__ == "__main__":
    parent_path = r"C:\Users\OWNER\Downloads\LIV (4)\LIV"  # Change this to your target directory
    for root, dirs, files in os.walk(parent_path):
        for file in files:
            file_path = os.path.join(root, file)
            if not file.endswith('.csv') or file.endswith('loss_data.csv'):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")

    print("Cleanup complete. All non-CSV files and 'loss_data.csv' files have been deleted.")
