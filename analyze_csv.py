import pandas as pd
import sys
import io

# Set UTF-8 encoding for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

df = pd.read_csv('data/Copy of ElectionResults (2016).csv', skiprows=2, low_memory=False)

print('=== RACE COLUMN ANALYSIS ===\n')

# President columns
pres_cols = [col for col in df.columns if 'President Candidates - ' in col and 'Vice' not in col]
print(f'President columns: {len(pres_cols)}')

# Check for unique non-empty values in first President column
if pres_cols:
    first_pres_col = pres_cols[0]
    non_empty = df[first_pres_col].dropna()
    non_empty = non_empty[non_empty != '']
    print(f'\nTotal non-empty values in {first_pres_col}: {len(non_empty)}')
    print(f'Unique candidates: {non_empty.nunique()}')
    print('\nSample values:')
    for val in list(non_empty.head(10)):
        print(f'  "{val}"')

    # Check for special values like "Abstain"
    abstain_vals = non_empty[non_empty.str.lower().str.contains('abstain', na=False)]
    print(f'\n"Abstain" values found: {len(abstain_vals)}')

    # Check for values without pipe separator
    non_pipe = non_empty[~non_empty.str.contains(r'\|', na=False, regex=True)]
    if len(non_pipe) > 0:
        print(f'\nNon-standard values (no pipe |): {len(non_pipe)}')
        for val in list(non_pipe.unique()[:10]):
            print(f'  "{val}"')

print('\n=== SENATE COLUMN ANALYSIS ===')
senate_cols = [col for col in df.columns if 'Senate Candidates - ' in col]
print(f'Senate columns found: {len(senate_cols)}')

# Check distribution of non-empty cells
if senate_cols:
    for i, col in enumerate(senate_cols[:5]):
        total = len(df[col])
        non_empty_count = df[col].notna().sum() - (df[col] == '').sum()
        print(f'{col}: {non_empty_count}/{total} non-empty ({100*non_empty_count/total:.1f}%)')

print('\n=== ALL COLUMN NAMES ===')
print(f'Total columns: {len(df.columns)}')
print('\nUnique race prefixes:')
prefixes = set()
for col in df.columns:
    if ' - ' in col:
        prefix = col.split(' - ')[0]
        prefixes.add(prefix)

for prefix in sorted(prefixes):
    cols_with_prefix = [c for c in df.columns if c.startswith(prefix)]
    print(f'  {prefix}: {len(cols_with_prefix)} columns')
