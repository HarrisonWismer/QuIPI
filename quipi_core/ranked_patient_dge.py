import quipi_shared as sh

import plotly.express as px
import plotly.graph_objects as go

import numpy as np
import pandas as pd

from statsmodels.stats.multitest import multipletests
from scipy.stats import ranksums

import gene_factor as gf



def highlight_boxplot(top_data,bot_data,highlight_genes):
   if len(highlight_genes) != 0:
      top_data_highlight = top_data[highlight_genes]
      bot_data_highlight = bot_data[highlight_genes]
      top_data_highlight["group"] = "Top Quartile Group"
      bot_data_highlight["group"] = "Bottom Quartile Group"

      comb_df = pd.concat((top_data_highlight,bot_data_highlight)).reset_index().drop(columns="index").melt(id_vars = ["group"])

      fig = px.box(comb_df, x="variable", y = "value",color = "group",
                labels = {"variable":"Gene", "value": "TPM", "group":"Group"})
   
      fig.update_layout(template = "simple_white",
                        legend=dict(y=0.5,  # Center vertically
                        font=dict(size=14)))
      return fig
   
   else:
      return None
    


def factor_ranked_dge(gfs_genes, gfs_compartment, quantile, dge_compartment,fc_threshold=1, p_val_thresh=0.000001, highlight_genes=[]):
   
   gfs = gf.calculate_gene_factor_score(gfs_genes, gfs_compartment)
   quipi_raw = pd.read_feather("./quipi_data/quipi_raw_tpm.feather")

   top_data, bot_data = rank_using_score(gfs, quipi_raw,"factor_score", quantile, dge_compartment)
   change_df = do_dge(top_data, bot_data)
   sig_pos, sig_neg = filter_dge(change_df, fc_threshold, p_val_thresh)
   fig = plot_dge(change_df,fc_threshold,p_val_thresh,highlight_genes)

   highlighted_boxplot = highlight_boxplot(top_data,bot_data,highlight_genes)

   return fig, sig_pos, sig_neg, highlighted_boxplot
        


def feature_ranked_dge(feature_score,compartment,quantile, fc_threshold= 1, p_val_thresh=0.000001,highlight_genes=[]):

   rank_cat = sh.feature_scores[feature_score]
   comp = compartment
   quantile = quantile
   
   flow_df = pd.read_feather("./quipi_data/quipi_flow_scores.feather",columns=["sample_name", sh.feature_scores[feature_score]])
   quipi_raw = pd.read_feather("./quipi_data/quipi_raw_tpm.feather")
   
   top_data, bot_data = rank_using_score(flow_df, quipi_raw, rank_cat, quantile, comp)
   change_df = do_dge(top_data, bot_data)
   sig_pos, sig_neg = filter_dge(change_df, fc_threshold, p_val_thresh)
   fig = plot_dge(change_df,fc_threshold,p_val_thresh,highlight_genes)

   highlighted_boxplot = highlight_boxplot(top_data,bot_data,highlight_genes)

   return fig, sig_pos, sig_neg, highlighted_boxplot




def rank_using_score(df, quipi_raw, rank_cat, quantile, comp):
   top_patients = df[df[rank_cat] > df[rank_cat].quantile(1 - quantile)][["sample_name", rank_cat]]
   bot_patients = df[df[rank_cat] < df[rank_cat].quantile(quantile)][["sample_name", rank_cat]]

   top = quipi_raw[(quipi_raw["sample_name"].isin(top_patients["sample_name"])) & (quipi_raw["compartment"] == comp)]

   bot = quipi_raw[(quipi_raw["sample_name"].isin(bot_patients["sample_name"])) & (quipi_raw["compartment"] == comp)]

   top_data = top[sh.genes]
   bot_data = bot[sh.genes]

   return top_data,bot_data

def do_dge(group1, group2):
   p_vals = ranksums(group1,group2)[1]
   p_adj = multipletests(p_vals, method = "fdr_bh")[1]

   g1_avg_tpm = group1.mean(axis=0) + .01
   g2_avg_tpm = group2.mean(axis=0) + .01

   fc = np.log2(g1_avg_tpm / g2_avg_tpm)
   log_p_val = -np.log10(p_adj)

   fchange_df = pd.DataFrame({"Gene":fc.index,
                             "Log2(FC)":fc,
                             "P-Value": p_vals,
                             "P-Value Adj." : p_adj,
                             "log10_p_val":log_p_val})
   
   return fchange_df

def determine_dge(df, fc_thresh, p_val_thresh):
      if df["Log2(FC)"] < -fc_thresh and df["log10_p_val"] > p_val_thresh:
            return "negative_sig"
      elif df["Log2(FC)"] > fc_thresh and df["log10_p_val"] > p_val_thresh:
            return "positive_sig"
      else:
            return "nonsig"

def filter_dge(fc_df, fc_thresh, p_thresh):
   fc_df["sig_call"] = fc_df.apply(determine_dge,axis=1,args = (fc_thresh,p_thresh))

   keep_cols = ["Gene", "Log2(FC)", "P-Value","P-Value Adj."]
   sig_pos = fc_df[fc_df["sig_call"] == "positive_sig"].sort_values(by = ["log10_p_val", "Log2(FC)"],ascending=False)[keep_cols]
   sig_neg = fc_df[fc_df["sig_call"] == "negative_sig"].sort_values(by = ["log10_p_val", "Log2(FC)"],ascending=False)[keep_cols]
    
   return sig_pos, sig_neg

def plot_dge(fc_df, fc_threshold,p_val_thresh,highlight_genes):

   fc_df['label_display'] = fc_df['Gene'].apply(lambda x: x if x in highlight_genes else "")

   # Create the scatter plot with Plotly Express
   #fig = px.scatter(df, x='x', y='y', text='label_display')
   
   fig = px.scatter(fc_df,x = "Log2(FC)", y = "log10_p_val",
      hover_data={"Gene"},
      labels = {"Log2(FC)":"Log2(FC)", "log10_p_val": "-log10(P-Value)"},
      #text = "label_display",
      color="sig_call",
      color_discrete_map={"positive_sig":"red", "nonsig":"black","negative_sig":"blue"})
   
   for i, label in enumerate(fc_df['label_display']):
    if label in highlight_genes:
        x=fc_df["Log2(FC)"][i]
        y=fc_df["log10_p_val"][i]

        if x < 0:
            ax = -1
        else:
            ax = 1
        fig.add_annotation(
            x=x,
            y=y,
            text=label,
            showarrow=True,
            arrowhead=2,
            ax= ax * 200,
            ay=-25,
            font=dict(size=12, color="black"),  # text color
            bgcolor="lime",  # bright green background
            borderpad=2,    # padding around text
            bordercolor="green",  # border color for the box
            borderwidth=1   # border width for the box
        )
   
   log_p_val_max = max(fc_df["log10_p_val"])
   fig.add_shape(
    type="line",
    x0=fc_threshold, x1=fc_threshold,  # Start and end points of the x-axis
    y0=-.00001, y1=log_p_val_max * 1.1,  # Cover the entire y-axis range
    line=dict(color="Red", width=2, dash="dash"),  # Line style
    )
   
   fig.add_shape(
    type="line",
    x0=-fc_threshold, x1=-fc_threshold,  # Start and end points of the x-axis
    y0=-.00001, y1=log_p_val_max * 1.1,  # Cover the entire y-axis range
    line=dict(color="Red", width=2, dash="dash"),  # Line style
    )

   #fig.update_layout(autosize=False, width=700, height=700)
   fc_abs_max = abs(max(fc_df["Log2(FC)"],key=abs))
   fig.update_layout(xaxis=dict(range=[-fc_abs_max-1, fc_abs_max+1]))
   fig.update_layout(template='simple_white')
   fig.update_layout(showlegend=False)

   fig.add_shape(
    type="line",
    x0=-fc_abs_max-1, x1=fc_abs_max+1,  # Start and end points of the x-axis
    y0=p_val_thresh, y1=p_val_thresh,  # Cover the entire y-axis range
    line=dict(color="Red", width=2, dash="dash"),  # Line style
    )

   return fig
    
    
def plot_fc_table(df, sign):
   fig = go.Figure(data=[go.Table(header=dict(values=list(df.columns),
                                              fill_color='white',
                                              line_color = "black",
                                              font = dict(color = "black",size = 18),
                                              align='center'),
                                 cells=dict(values=[df[col].map(lambda x: f"{x:.4f}") if df[col].dtype != object else df[col] for col in df.columns],
                                            line_color='black',
                                            align='center',
                                            height=30,
                                            font = dict(color = 'black', size = 18)))])

   if sign == "Negative":
      fig.update_layout(title="Top Negative DGEs", title_x= .5)
   else:
       fig.update_layout(title="Top Positive DGEs", title_x= .5)
        
   return fig
