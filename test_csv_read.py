import pandas as pd

csv_path = r'C:\Users\jsheri1\Desktop\20251030_SiEPICfab_Shuksan_24_02_RepeatedSweeps\Trial1-Cycle10_Run10\Benchtop\2025_10_31_16_12_47_cycle01_run01_BENCH\2025_10_31_16_12_47_C01_R01_Benchtop_1330nm_ChipD30_R4\2025_10_31_16_12_47_C01_R01_Benchtop_1330nm_ChipD30_R4.csv'

df = pd.read_csv(csv_path, header=None, engine='python', skiprows=23)

print(f"Total rows: {len(df)}")
print(f"Total columns: {len(df.columns)}")
print(f"\nFirst column values:")

for i in range(min(10, len(df))):
    val = str(df.loc[i, 0])
    print(f"Row {i}: {val}")



