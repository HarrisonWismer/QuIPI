from shiny import App, render, ui, reactive
import plotly.express as px
from shinywidgets import output_widget, render_widget 
from plotly.subplots import make_subplots
import plotly.graph_objects as go

import shared as sh

import numpy as np
import pandas as pd
pd.options.plotting.backend = 'plotly'
import matplotlib.pyplot as plt


from scipy.stats import zscore
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests
from scipy.stats import ranksums

import quipi_dash_core.ranked_patient_dge as rpd
import quipi_dash_core.gene_factor as gf


# Define the UI
app_ui = ui.page_fluid(

    # ENTIRE PAGE TITLE
    ui.panel_title("QuIPI - Querying IPI"),

        # Create navigation tab bar containing a tab for each GUI function.
        ui.navset_tab(
            
            # Home tab with useful information, references etc.
            ui.nav_panel("Home",
                ui.h2("Welcome to QuIPI"), 
                ui.p("Here are some useful references."),
                ui.layout_column_wrap(
                    output_widget("pancan_archetypes"),
                    output_widget("cancer_glossary"))
            ),

            # Box/Violin plot where the user selects a gene and can group by custom categories
            ui.nav_panel("Box/Violin Plots",
                ui.page_sidebar(
                    ui.sidebar(
                        ui.input_selectize("box_viol_plot",
                                           "Select Plot Type:",
                                           ["Boxplot","Violin Plot"]),
                        ui.input_selectize("box_viol_gene_input",
                                           "Select Gene:",
                                           sh.genes),
                        ui.input_selectize("box_viol_x_category",
                                           "Select X-Axis Category:",
                                           list(sh.categoricals_dict.keys())),
                        ui.input_selectize("box_viol_groupby",
                                           "Group by:",
                                           list(sh.categoricals_dict.keys())),
                        ui.input_selectize("box_viol_transformation",
                                           "Choose Transformation: ",
                                           ["Raw", "Log2", "Log10"],
                                           multiple= False,
                                           selected= "Log2")),             
                        output_widget("expression_box_viol")
                )
            ),

            # Pairwise correlation plot between user-defined genes.
            ui.nav_panel("Correlation Plots",
                ui.page_sidebar(
                    ui.sidebar("Explore the correlation of selected genes.",
                    ui.input_action_button("corr_run", "Run"),
                    ui.input_selectize("corr_gene_input",
                                       "Select Genes:",
                                       sh.genes,
                                       multiple=True),
                    ui.input_selectize("corr_indication",
                                       "Select Indications:",
                                       list(sh.quipi_raw["indication"].unique()),
                                       multiple = True),
                    ui.input_selectize("corr_tissue",
                                       "Select Tissue:",
                                       ["Tumor", "Normal"],
                                       multiple = True),
                    ui.input_selectize("corr_compartment",
                                       "Select Compartments:",
                                       list(sh.quipi_raw["compartment"].unique()),
                                       multiple=True),
                    ui.input_selectize("corr_archetype",
                                       "Select Archetypes:",
                                       list(sh.quipi_raw["archetype"].unique()),
                                       multiple=True),
                    ui.input_selectize("corr_transform",
                                       "Select Transformation:",
                                       ["Raw", "Log2", "Log10"],
                                       selected="Log2"),
                    ui.input_selectize("corr_method_input",
                                       "Select Method:",
                                       ["Pearson", "Spearman"],
                                       selected="Spearman")),
                output_widget("gene_correlation_heatmap")
                )
            ),

            ui.nav_menu("PanCan Archetype UMAP",

                # Tab where user can select multiple eachs and view their expression overlayed on the individual
                # PanCan UMAPs
                ui.nav_panel("PanCan UMAP Gene Expression",
                    ui.page_sidebar(
                        ui.sidebar(
                            ui.h3("PanCan UMAP Gene Expression"),
                            ui.input_selectize("pancan_gene_input",
                                                "Select Genes:",
                                                sh.genes,
                                                multiple = True),
                            ui.input_selectize("pancan_compartment_input",
                                            "Select Compartment:",
                                            list(sh.quipi_raw["compartment"].unique())
                                            ),
                            ui.input_selectize("pancan_umap_transformation",
                                            "Choose Transformation:",
                                            ["Raw", "Log2", "Log10"],
                                            multiple= False,
                                            selected= "Log2")
                            ),
                            ui.layout_columns(output_widget("pancan_subplots"))
                    )
                ),

                # Given user-defined gene list, plots the gene factor score on top of the PanCan UMAP
                ui.nav_panel("PanCan Gene Factor Scores",
                    ui.page_sidebar(
                        ui.sidebar(
                            ui.h3("PanCan Gene Factor Scores"),
                            ui.input_action_button("gene_factor_run", "Run"),
                            ui.input_selectize("gene_factor_genes",
                                                "Select Genes:",
                                                sh.genes,
                                                multiple=True),
                            ui.input_selectize("gene_factor_compartment",
                                            "Select Compartment:",
                                            list(sh.quipi_raw["compartment"].unique()))
                        ),
                        output_widget("gene_factor_analysis")
                    )
                )
            ),

            ui.nav_menu("Ranked DGE",
                # Differential Gene Expression (DGE) between the top and bottom quantiles
                # of patients based on pre-calculated IPI feature scores.
                ui.nav_panel("Feature Score Ranked DGE",
                    ui.page_sidebar(
                        ui.sidebar(
                            ui.h1("Feature Score Ranked DGE"),
                            ui.input_action_button("dge_run", "Run"),
                            ui.input_selectize("flow_score_to_rank",
                                            "Feature Score For Ranking:",
                                            list(sh.feature_scores.keys())),
                            ui.input_slider("dge_slider",
                                            "Quartile:",
                                            value = .2,
                                            min = 0.05,
                                            max = .5,
                                            step = .05),
                            ui.input_selectize("dge_compartment",
                                                "DGE Compartment:",
                                                list(sh.quipi_raw["compartment"].unique())),
                            ui.input_numeric("dge_fc_thresh",
                                            "Compartment for DGE:",
                                            value=2),
                            ui.input_numeric("dge_p_thresh",
                                            "P-Value Threshold:",
                                            value = .00001)
                        ),
                        ui.layout_column_wrap(
                            output_widget("compartment_featurescore_dge")
                        )
                    )
                ),

                # DGE between the top and bottom quantiles of patients based on
                # gene factor scores calculated from a collection of genes.
                ui.nav_panel("Factor Score Ranked DGE",
                    ui.page_sidebar(
                        ui.sidebar(
                            ui.h1("Factor Score Ranked DGE"),
                            ui.input_action_button("fs_dge_run","Run"),
                            ui.input_selectize("fs_dge_genes",
                                            "Genes for gene-factor score:",
                                            sh.genes,
                                            multiple=True),
                            ui.input_selectize("fs_dge_compartment",
                                            "Compartment to calculate gene-factor score:",
                                            list(sh.quipi_raw["compartment"].unique())),
                            ui.input_slider("fs_dge_slider",
                                            "Quartile:",
                                            value = .2,
                                            min = 0.05, max = .5,
                                            step = .05),
                            ui.input_selectize("fs_dge_compartment_for_dge",
                                            "Compartment for DGE:",
                                            list(sh.quipi_raw["compartment"].unique())),
                            ui.input_numeric("fs_dge_fc_thresh",
                                            "Fold Change Threshold",
                                            value = 2),
                            ui.input_numeric("fs_dge_p_thresh",
                                            "P-Value Threshold",
                                            value=.00001)
                            ),
                        output_widget("gfs_ranked_dge")
                    )
                )
            )
        ),
    title = "QuIPI - Querying IPI"
)

def server(input, output, session):

    @render_widget
    def pancan_subplots():
        
        transform = input.pancan_umap_transformation()
        genes = input.pancan_gene_input()
        compartment = input.pancan_compartment_input()
        input_arr = sh.transformations[transform]
        input_arr = input_arr[input_arr["compartment"] == compartment]



        if len(genes) != 0:

            n_col = min(4,len(genes))
            n_rows = (len(genes) + n_col - 1) // n_col

            fig = make_subplots(rows =  n_rows , cols = n_col, 
                                subplot_titles=genes,
                                vertical_spacing=.05,horizontal_spacing=.02,
                                shared_xaxes=True,shared_yaxes=True)


            for count, gene in enumerate(genes):
                
                row = count // n_col
                col = count % n_col

                scatter = go.Scatter(x = input_arr["x_umap1"], y = input_arr["x_umap2"],
                                        mode = 'markers',
                                        marker=dict(
                                            size=10,  # Adjust marker size if needed
                                            color=input_arr[gene],  # Color by the numerical value
                                            colorscale='Viridis',
                                            #colorbar=dict(title=gene,x=(1+col)*.4756,y = (1+row) * .5)#xanchor="right",yanchor="middle")  # Choose a colorscale (e.g., Viridis, Plasma, etc.)),
                                            ))
                
                fig.add_trace(scatter, row= row+1, col= col+1)
            
            fig.update_layout(height=300*n_rows, width=300*n_col, showlegend=False)
            fig.update_xaxes(scaleanchor="y", scaleratio=1, showticklabels=False)
            fig.update_yaxes(scaleanchor="x", scaleratio=1, showticklabels=False)

            return fig
        
    @render_widget
    def cancer_glossary():
        df = sh.cancer_glossary_df

        fig = go.Figure(data=[go.Table(
            header=dict(values=list(df.columns),
                        fill_color='white',
                        font = dict(color = "black",size = 18),
                        align='center'),
            cells=dict(values=[df[col] for col in df.columns],
                    fill_color=[[sh.colors_indic[color] for color in df["Abbreviation"]]],  # Apply row colors
                    align='center',
                    height=30,
                    font = dict(color = 'white', size = 18)))
        ])
        
        fig.update_layout(autosize=False, width=600,height=800)
        return fig
        
    @render_widget
    def pancan_archetypes():
        fig = px.scatter(sh.pancan_only_raw, x = "x_umap1", y="x_umap2", 
                         color="archetype", color_discrete_map=sh.colors_pancan)
        fig.update_traces(marker=dict(size=12))
        fig.update_layout(legend_title_text = "Archetype")
        fig.update_layout(autosize=False, width=650, height=500,template = "simple_white")
        fig.update_yaxes(visible=False)
        fig.update_xaxes(visible=False)
   
        return fig

    @render_widget
    def expression_box_viol():

        transform = input.box_viol_transformation()
        x_cat = sh.categoricals_dict[input.box_viol_x_category()]

        input_arr = sh.transformations[transform]

        gene = input.box_viol_gene_input()
        group = sh.categoricals_dict[input.box_viol_groupby()]

        if gene is not None and gene != "" and gene != []:
            if input.box_viol_plot() == "Boxplot":
                fig = px.box(input_arr, x = x_cat, y = gene, color = group,
                            color_discrete_sequence=px.colors.qualitative.D3,
                            labels=sh.categoricals_dict_reversed)
            else:
                fig = px.violin(input_arr, x = x_cat, y = gene, color = group,
                                color_discrete_sequence=px.colors.qualitative.D3,
                                labels=sh.categoricals_dict_reversed)
                
            fig.update_layout(title_text= gene + " " + transform + "(TPM)", title_x=0.5)
            return fig
    

    @render.data_frame
    def gene_corr_df():
        genes = list(input.corr_gene_input())
        indications = input.corr_indication()
        method = sh.corr_methods[input.corr_method_input()]
        compartments = input.corr_compartment()
        archetypes = input.corr_archetype()
        tissues = [sh.tissue_dict[tis] for tis in input.corr_tissue()]

        transform = input.corr_transform()

        input_arr = sh.transformations[transform]
        input_arr = input_arr[input_arr["indication"].isin(indications)]
        input_arr = input_arr[input_arr["compartment"].isin(compartments)]
        input_arr = input_arr[input_arr["archetype"].isin(archetypes)]
        input_arr = input_arr[input_arr["sample_type_cat"].isin(tissues)]
        input_arr = input_arr[genes]

        return input_arr


    @render_widget
    @reactive.event(input.corr_run)
    def gene_correlation_heatmap():

        genes = list(input.corr_gene_input())
        indications = input.corr_indication()
        method = sh.corr_methods[input.corr_method_input()]
        compartments = input.corr_compartment()
        archetypes = input.corr_archetype()
        tissues = [sh.tissue_dict[tis] for tis in input.corr_tissue()]


        transform = input.corr_transform()

        input_arr = sh.transformations[transform]
        input_arr = input_arr[input_arr["indication"].isin(indications)]
        input_arr = input_arr[input_arr["compartment"].isin(compartments)]
        input_arr = input_arr[input_arr["archetype"].isin(archetypes)]
        input_arr = input_arr[input_arr["sample_type_cat"].isin(tissues)]
        input_arr = input_arr[genes]

        corr_df = input_arr.corr(method=method)

        # Create a mask for the upper triangle
        mask = np.triu(np.ones_like(corr_df, dtype=bool))

        # Apply the mask to the correlation matrix
        corr_lower_tri = corr_df.mask(mask)

        corr_lower_tri = corr_lower_tri.dropna(axis=0, how = "all")
        corr_lower_tri = corr_lower_tri.dropna(axis=1, how = "all")

        fig = px.imshow(corr_lower_tri.fillna(""),
                        zmin = -1, zmax =1,
                        color_continuous_scale = "RdBu_r",
                        text_auto=True)
        fig.update_layout(template='simple_white', coloraxis_colorbar_x=.8)
        fig.update_xaxes(showgrid=False, showline=False)
        fig.update_yaxes(showgrid=False, showline=False)

        return fig
    
    @render_widget
    @reactive.event(input.gene_factor_run)
    def gene_factor_analysis():
        
        gene_set = list(input.gene_factor_genes())
        compartment = input.gene_factor_compartment()
        log2_subset_full = gf.calculate_gene_factor_score(gene_set, compartment)

        fig = px.scatter(log2_subset_full, x = "x_umap1", y = "x_umap2", 
                         color = "factor_score", color_continuous_scale="viridis",
                         labels = {"factor_score" : "Factor Score"})

        fig.update_layout(template="simple_white", autosize=False, width=650, height=500,
                          legend_title_text = "Factor Score")
        
        fig.update_traces(marker=dict(size=12))
        fig.update_layout(legend_title_text = "Archetype")
        fig.update_yaxes(visible=False)
        fig.update_xaxes(visible=False)
        return fig

    
    @render_widget
    @reactive.event(input.dge_run)
    def compartment_featurescore_dge():
        return rpd.feature_ranked_dge(input.flow_score_to_rank(), 
                                      input.dge_compartment(), 
                                      input.dge_slider(),
                                      input.dge_fc_thresh(),
                                      input.dge_p_thresh())[0]
    

    @render_widget
    @reactive.event(input.fs_dge_run)
    def gfs_ranked_dge():
        gfs_genes = list(input.fs_dge_genes())
        gfs_compartment = input.fs_dge_compartment()

        dge_quantile = input.fs_dge_slider()
        dge_compartment = input.fs_dge_compartment_for_dge()

        fc_thresh = input.fs_dge_fc_thresh()
        p_thresh = input.fs_dge_p_thresh()

        fig = rpd.factor_score_ranked_dge(gfs_genes,gfs_compartment,dge_quantile,dge_compartment, fc_thresh, p_thresh)

        return fig


# Create the Shiny app
app = App(app_ui, server)

# Run the app
#app.run()


