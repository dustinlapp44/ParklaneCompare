def float_conv(x):
    if isinstance(x, str):
        x = x.replace(",", "")
    try:
        return float(x)
    except:
        return 0.0

def pmc_data_cleanup(df):
    df['Gross'] = df['Gross'].apply(float_conv)
    return df

def property_data_cleanup(df):
    df['Amount'] = df['Amount'].apply(float_conv)
    return df
