import numpy as np
import pandas as pd
from scipy.stats import zscore
import shared as sh

def calculate_gene_factor_score(gene_set,compartment):

    input_arr = pd.read_feather("./data/quipi_log2_tpm.feather", columns=sh.non_genes + gene_set)
    log2_subset = input_arr[input_arr["archetype"] != "Unclassified"][input_arr["compartment"] == compartment][sh.non_genes+gene_set]

    z_subset = log2_subset[gene_set].apply(zscore)
    z_subset["factor_score"] = z_subset.mean(axis=1)
    log2_subset_full = log2_subset[sh.non_genes].merge(z_subset,left_index=True,right_index=True)

    return log2_subset_full