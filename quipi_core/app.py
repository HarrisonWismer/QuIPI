from shiny import App, render, ui, reactive
from shinyswatch import theme
import plotly.express as px
from shinywidgets import output_widget, render_widget 

import shared as sh

import numpy as np
import pandas as pd
from io import StringIO

import ranked_patient_dge as rpd
import gene_factor as gf
import box_viol_expression_plot as bv
import pancan_plots as pp
import correlation_analysis as corr

RUN_STYLE="background-color: #AFE1AF; color: black;"

# Define the UI
app_ui = ui.page_navbar(

        ui.nav_panel("Home",
            ui.panel_title("Welcome to QuIPI",), 
            ui.p("Here are some useful references."),
            ui.layout_column_wrap(
                ui.card(ui.card_header("Cancer Indication Breakdown"),
                        output_widget("plot_indication_breakdown"), 
                        full_screen=False,
                        ),
                ui.card(ui.card_header("Cancer Indication Nomenclature"),
                    output_widget("cancer_glossary"),
                    full_screen=False),
                ui.card(ui.card_header("PanCan Archetype UMAP"),
                        ui.card_body(output_widget("pancan_archetypes_home")),
                        ui.card_footer(
                            ui.HTML(f'<a href="{"https://pubmed.ncbi.nlm.nih.gov/34963056/"}" target="_blank">Discovering dominant tumor immune archetypes in a pan-cancer census. Combes AJ, Samad B, Tsui J, et al. Cell. 2022</a>')
                        ),
                        full_screen=False,     
                ),
                ui.card(ui.card_header("PanCan Archetype Breakdown"),
                        ui.card_body(output_widget("pancan_archetype_breakdown")),
                        ui.card_footer("""
                                       Nota Bene: Unclassified patients do not have Feature Scores assigned to them.
                                       Any calculations involving a feature score are subset to include archetyped patients only.
                                       """)),
            width=.5)
        ),

        # Box/Violin plot where the user selects a gene and can group by custom categories
        ui.nav_panel("Box/Violin Plots",
            ui.layout_sidebar(
                ui.sidebar(
                    ui.h4("Explore gene expression by category"),
                    ui.input_action_button("box_viol_run", "Run", style=RUN_STYLE),
                    ui.input_selectize("box_viol_plot",
                                        "Select Plot Type:",
                                        ["Boxplot","Violin Plot"]),
                    ui.input_selectize("box_viol_gene_input",
                                        "Select Genes:",
                                        [],
                                        multiple=True),
                    ui.input_selectize("box_viol_x_category",
                                        "Select X-Axis Category:",
                                        list(sh.categoricals_dict.keys()),
                                        selected = "Compartment"),
                    ui.input_selectize("box_viol_groupby",
                                        "Group by:",
                                        list(sh.categoricals_dict.keys()),
                                        selected="Archetype"),
                    ui.input_selectize("box_viol_transformation",
                                        "Choose Transformation: ",
                                        ["Raw", "Log2"],
                                        multiple= False,
                                        selected= "Log2")),
            output_widget("expression_box_viol")
            ),
        ),

        # Pairwise correlation plot between user-defined genes.
        ui.nav_menu("Correlation Plots",

            ui.nav_panel("Correlation Matrix",
                ui.layout_sidebar(
                    ui.sidebar(
                        ui.h4("Explore the correlation of selected genes."),
                        ui.input_action_button("corr_run", "Run",style=RUN_STYLE),
                        ui.input_selectize("corr_gene_input",
                                            "Select Genes:",
                                            [],
                                            multiple=True,
                                            options = {'server':True}),
                        ui.input_selectize("corr_indication",
                                            "Select Indications:",
                                            choices=sh.indications,
                                            selected=sh.indications,
                                            multiple = True),
                        ui.input_selectize("corr_tissue",
                                            "Select Tissue:",
                                            choices=["Tumor", "Normal"],
                                            selected = ["Tumor", "Normal"],
                                            multiple = True),
                        ui.input_selectize("corr_compartment",
                                            "Select Compartments:",
                                            choices=sh.compartments,
                                            selected=sh.compartments,
                                            multiple=True),
                        ui.input_selectize("corr_archetype",
                                            "Select Archetypes:",
                                            choices=sh.archetypes,
                                            multiple=True,
                                            selected=sh.archetypes),
                        ui.input_selectize("corr_transform",
                                            "Select Transformation:",
                                            choices=["Raw", "Log2"],
                                            selected="Log2"),
                        ui.input_selectize("corr_method_input",
                                            "Select Method:",
                                            choices=["Pearson", "Spearman"],
                                            selected="Spearman")),
                ui.card(ui.card_body(output_widget("gene_correlation_heatmap")),
                        ui.card_footer("Click button in the bottom right for fullscreen view."),
                        full_screen=True)
                )
            ),

            ui.nav_panel("Categorical Correlation Comparison",
                ui.h3("Functionality Coming Soon."),
                ui.layout_sidebar(
                        ui.sidebar(
                            ui.h4("Explore the correlation of genes between two chosen categories."),
                            #ui.input_action_button("corr_run", "Run",style=RUN_STYLE),

                            ui.input_selectize("corr_cat_gene_input",
                                                "Select Gene:",
                                                [],
                                                multiple=False,
                                                options = {'server':True}),
                        ),
                    ui.card("Test")
                    )
            )
        ),

        ui.nav_menu("PanCan Archetype UMAP",

            # Tab where user can select multiple eachs and view their expression overlayed on the individual
            # PanCan UMAPs
            ui.nav_panel("PanCan UMAP Gene Expression",
                ui.layout_sidebar(
                    ui.sidebar(
                        ui.h4("PanCan UMAP Gene Expression"),
                        ui.input_action_button("pancan_umap_run", "Run",style=RUN_STYLE),
                        ui.input_selectize("pancan_gene_input",
                                            "Select Genes:",
                                            [],
                                            multiple = True),
                        ui.input_selectize("pancan_compartment_input",
                                        "Select Compartment:",
                                        sh.compartments
                                        ),
                        ui.input_selectize("pancan_umap_transformation",
                                        "Choose Transformation:",
                                        ["Raw", "Log2"],
                                        multiple= False,
                                        selected= "Log2")
                        ),
                        output_widget("pancan_subplots")
                ),
            ),

            # Given user-defined gene list, plots the gene factor score on top of the PanCan UMAP
            ui.nav_panel("PanCan Gene-Signature Overlay",
                ui.layout_sidebar(
                    ui.sidebar(
                        ui.h4("PanCan Gene-Signature Overlay"),
                        ui.input_action_button("gene_factor_run", "Run",style=RUN_STYLE),
                        ui.input_selectize("gene_factor_genes",
                                            "Select Genes:",
                                            [],
                                            multiple=True),
                        ui.input_selectize("gene_factor_compartment",
                                        "Select Compartment:",
                                        sh.compartments)
                    ),
                    ui.layout_column_wrap(
                        ui.card(ui.card_body(output_widget("gene_factor_analysis"))),
                        ui.card(ui.card_body(output_widget("pancan_archetypes_gfs")))
                    )
                ),
                ui.h5("Gene-Signature Score Calculation"),
                ui.p("""
                    Data is subset to include archetyped patients only within a given compartment.
                    Gene-signature scores are calculated by first calculating a per-gene Z-Score across patients
                    and subsequently averaging the Z-Scores within each patient resulting in each patient being
                    assigned a gene-signature score depending on their expression of the input gene set.

                    """)
            )
        ),

        ui.nav_menu("Ranked DGE",
            # Differential Gene Expression (DGE) between the top and bottom quantiles
            # of patients based on pre-calculated IPI feature scores.
            ui.nav_panel("Feature Score Ranked DGE",
                ui.layout_sidebar(
                    ui.sidebar(
                        ui.h4("Feature Score Ranked DGE"),
                        ui.input_action_button("dge_run", "Run",style=RUN_STYLE),
                        ui.input_selectize("flow_score_to_rank",
                                        "Feature Score For Ranking:",
                                        list(sh.feature_scores.keys())),
                        ui.input_selectize("dge_highlight_genes",
                                           "Genes of interest to be highlighted.",
                                           [],
                                            multiple=True),
                        ui.input_slider("dge_slider",
                                        "Quartile:",
                                        value = .2,
                                        min = 0.05,
                                        max = .5,
                                        step = .05),
                        ui.input_selectize("dge_compartment",
                                            "DGE Compartment:",
                                            sh.compartments),
                        ui.input_numeric("dge_fc_thresh",
                                        "Log2FC Threshold:",
                                        value=2),
                        ui.input_numeric("dge_p_thresh",
                                        "-Log10(P-Value) Threshold:",
                                        value = 1)
                    ),
                    output_widget("compartment_featurescore_dge"),
                    ui.layout_column_wrap(
                        ui.card(
                            ui.card_header("Negative DGEs"),
                            ui.card_body(ui.output_data_frame("compartment_featurescore_dge_bot")),
                        ),
                        ui.card(
                            ui.card_header("Positive DGEs"),
                            ui.card_body(ui.output_data_frame("compartment_featurescore_dge_top"))
                        ),
                    ),
                    ui.download_button("download_featurescore_dges", "Download DGEs",),
                    ui.card(
                        ui.card_header("Expression Levels for genes of interest"),
                        ui.card_body(output_widget("compartment_featurescore_dge_boxplot"))
                    ),
                ),
                ui.h4("Feature Scoring and DGE Group Formation"),
                ui.p("""
                    Data is subset to include only patients assigned feature scores. Effectively, this means that
                    patients without an archetype designation are not considered. Patients are ranked based
                    on their feature score in the specified compartment and are split based on the specified
                    quartile. For the chose quartile, the resulting groups used for DGE are top quartile percent
                    of patients with the highest score and the bottom quartile percent of patients with the lowest score.
                """),
                ui.h4("Differential Gene Expression"),
                ui.p("""The Wilcoxon Rank-sum test is used to calculate differentially expressed genes.
                        P-values are corrected using Benjamini/Hochberg multiple testing correction.
                        """),
            ),

            # DGE between the top and bottom quantiles of patients based on
            # gene factor scores calculated from a collection of genes.
            ui.nav_panel("Gene-Signature Score Ranked DGE",
                ui.layout_sidebar(
                    ui.sidebar(
                        ui.h4("Gene-Signature Score Ranked DGE"),
                        ui.input_action_button("fs_dge_run","Run",style=RUN_STYLE),
                        ui.input_selectize("fs_dge_genes",
                                        "Genes for gene-signature score:",
                                        [],
                                        multiple=True),
                        ui.input_selectize("fs_dge_highlight_genes",
                                           "Genes of interest to be highlighted.",
                                           [],
                                            multiple=True),
                        ui.input_selectize("fs_dge_compartment",
                                        "Compartment to calculate gene-signature score:",
                                        sh.compartments),
                        ui.input_slider("fs_dge_slider",
                                        "Quartile:",
                                        value = .2,
                                        min = 0.05, max = .5,
                                        step = .05),
                        ui.input_selectize("fs_dge_compartment_for_dge",
                                        "Compartment for DGE:",
                                        sh.compartments),
                        ui.input_numeric("fs_dge_fc_thresh",
                                        "Fold Change Magnitude Threshold",
                                        value = 2),
                        ui.input_numeric("fs_dge_p_thresh",
                                        "-Log10(P-Value) Threshold",
                                        value=1),
                    ),
                    output_widget("gfs_ranked_dge"),
                    
                    ui.layout_column_wrap(

                        ui.card(ui.card_header("Negative DGEs"),
                                ui.card_body(ui.output_data_frame("gfs_ranked_dge_bot")),
                                max_height=500),
                        ui.card(ui.card_header("Positive DGEs"),
                                ui.card_body(ui.output_data_frame("gfs_ranked_dge_top")),
                                max_height=500),
                    ),
                ui.download_button("download_signaturecore_dges", "Download DGEs"),
                ui.card(
                    ui.card_header("Expression levels for genes of interest"),
                    ui.card_body(output_widget('gfs_ranked_dge_highlighted_exprn_box'))),
                ),

                ui.h4("Differential Gene Expression"),
                ui.p("""The Wilcoxon Rank-sum test is used to calculate differentially expressed genes.
                        P-values are corrected using Benjamini/Hochberg multiple testing correction.
                        """),
                ui.h5("Gene-Signature Score Calculation"),
                ui.p("""
                    Data is subset to include archetyped patients only within a given compartment.
                    Gene-signature scores are calculated by first calculating a per-gene Z-Score across patients
                    and subsequently averaging the Z-Scores within each patient resulting in each patient being
                    assigned a gene-signature score depending on their expression of the input gene set.

                    """)
            ),
            
        ),
    ui.nav_spacer(),
    ui.nav_control(
            ui.tags.img(
                src="./data/images/github.png",
                alt="GitHub",
                style="height: 50px; width: 50px;",
                href="https://github.com/your-profile"
            ),
            #href="https://github.com/your-profile",  # Replace with your GitHub URL
            #target="_blank",
            #class_="nav-link"
    ),
    title = "QuIPI - Querying IPI",
    theme=theme.lumen,
    bg= '#85aad4',
)

def server(input, output, session):
    @render_widget
    def cancer_glossary():
        return sh.plot_cancer_glossary_table()
    
    @render_widget
    def plot_indication_breakdown():
        return sh.plot_indication_breakdown()
    
    @render_widget
    def pancan_archetypes_home():
        fig = pp.plot_pancan_archetypes()
        fig.update_layout(autosize=False, width=650, height=500,template = "simple_white")
        return fig
    
    @render_widget
    def pancan_archetype_breakdown():
        return sh.plot_archetype_beakdown()
    
    @render_widget
    @reactive.event(input.gene_factor_run)
    def pancan_archetypes_gfs():
        fig = pp.plot_pancan_archetypes()
        fig.update_layout(autosize=False, width=600, height=450,template = "simple_white")
        return fig
        
    @render_widget
    @reactive.event(input.pancan_umap_run)
    def pancan_subplots():
        
        transform = input.pancan_umap_transformation()
        genes = input.pancan_gene_input()
        compartment = input.pancan_compartment_input()

        fig =pp.plot_pancan_exprn_subplots(transform, genes, compartment)
        return fig


    @render_widget
    @reactive.event(input.box_viol_run)
    def expression_box_viol():

        transform = input.box_viol_transformation()
        x_cat = sh.categoricals_dict[input.box_viol_x_category()]
        gene = input.box_viol_gene_input()
        group = input.box_viol_groupby()
        plot_type = input.box_viol_plot()

        fig = bv.box_viol_exprn(transform, x_cat, gene, group, plot_type)

        return fig


    @render_widget
    @reactive.event(input.corr_run)
    def gene_correlation_heatmap():

        genes = input.corr_gene_input()
        indications = input.corr_indication()
        method = sh.corr_methods[input.corr_method_input()]
        compartments = input.corr_compartment()
        archetypes = input.corr_archetype()
        tissues = [sh.tissue_dict[tis] for tis in input.corr_tissue()]
        transform = input.corr_transform()

        return corr.gene_correlation_heatmap(genes, indications, method, compartments, archetypes, tissues, transform)
    
    
    @render_widget
    @reactive.event(input.gene_factor_run)
    def gene_factor_analysis():
        
        gene_set = list(input.gene_factor_genes())
        compartment = input.gene_factor_compartment()
        log2_subset_full = gf.calculate_gene_factor_score(gene_set, compartment)

        fig = px.scatter(log2_subset_full, x = "x_umap1", y = "x_umap2", 
                         color = "factor_score", color_continuous_scale="viridis",
                         labels = {"factor_score" : "Factor Score"})

        fig.update_layout(template="simple_white", autosize=False, width=600, height=450,
                          legend_title_text = "Gene-Signature Score")
        
        fig.update_traces(marker=dict(size=12))
        fig.update_layout(legend_title_text = "Archetype")
        fig.update_yaxes(visible=False)
        fig.update_xaxes(visible=False)
        return fig
    


    # DGE by COMPARTMENT score
    @reactive.calc
    @reactive.event(input.dge_run)
    def feature_ranked_dge_reactive():

        fig, sig_pos, sig_neg, highlighted_boxplot = rpd.feature_ranked_dge(input.flow_score_to_rank(), 
                                      input.dge_compartment(), 
                                      input.dge_slider(),
                                      input.dge_fc_thresh(),
                                      input.dge_p_thresh(),
                                      list(input.dge_highlight_genes()))

        return fig, sig_pos, sig_neg, highlighted_boxplot

    
    @render_widget
    def compartment_featurescore_dge():
        return feature_ranked_dge_reactive()[0]
    
    @render.data_frame
    def compartment_featurescore_dge_top():
        return feature_ranked_dge_reactive()[1]
    
    @render.data_frame
    def compartment_featurescore_dge_bot():
        return feature_ranked_dge_reactive()[2]
    
    @render_widget
    def compartment_featurescore_dge_boxplot():
        boxplot = feature_ranked_dge_reactive()[3]
        if boxplot is not None:
            return boxplot
    
    @render.download(filename="FeatureScore_DGES.csv")
    def download_featurescore_dges():
        df = pd.concat([feature_ranked_dge_reactive()[1],feature_ranked_dge_reactive()[2]], axis = 0, ignore_index=True)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        yield csv_buffer.getvalue()


    # DGE by FACTOR score
    @reactive.calc
    @reactive.event(input.fs_dge_run)
    def factor_ranked_dge_reactive():
        
        if len(input.fs_dge_genes()) != 0:
            fig, sig_pos, sig_neg, highlight_boxplot = rpd.factor_ranked_dge(list(input.fs_dge_genes()),
                                                        input.fs_dge_compartment(),
                                                        input.fs_dge_slider(),
                                                        input.fs_dge_compartment_for_dge(),
                                                        input.fs_dge_fc_thresh(),
                                                        input.fs_dge_p_thresh(),
                                                        list(input.fs_dge_highlight_genes()))

            return fig, sig_pos, sig_neg, highlight_boxplot
        

    
    @render_widget
    def gfs_ranked_dge():
        return factor_ranked_dge_reactive()[0]

    
    @render.data_frame
    def gfs_ranked_dge_top():
        return factor_ranked_dge_reactive()[1]
    
    @render.data_frame
    def gfs_ranked_dge_bot():
        return factor_ranked_dge_reactive()[2]
    
    @render_widget
    def gfs_ranked_dge_highlighted_exprn_box():
        boxplot = factor_ranked_dge_reactive()[3]
        
        if boxplot != None :
            return boxplot
    
    @render.download(filename="SignatureScore_DGES.csv")
    def download_signaturecore_dges():
        df = pd.concat([factor_ranked_dge_reactive()[1],factor_ranked_dge_reactive()[2]], axis = 0, ignore_index=True)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        yield csv_buffer.getvalue()

        

    # Gene selection drop down inputs to make them computer server-side
    # otherwise the app takes an extremely long time to launch.
    @reactive.effect
    def _():
        ui.update_selectize(
            "box_viol_gene_input",
            choices=sh.genes,
            selected=[],
            server=True,
        )
    @reactive.effect
    def _():
        ui.update_selectize(
            "corr_gene_input",
            choices=sh.genes,
            selected=[],
            server=True,
        )
    @reactive.effect
    def _():
        ui.update_selectize(
            "pancan_gene_input",
            choices=sh.genes,
            selected=[],
            server=True,
        )
    @reactive.effect
    def _():
        ui.update_selectize(
            "gene_factor_genes",
            choices=sh.genes,
            selected=[],
            server=True,
        )
    @reactive.effect
    def _():
        ui.update_selectize(
            "fs_dge_genes",
            choices=sh.genes,
            selected=[],
            server=True,
        )

    @reactive.effect
    def _():
        ui.update_selectize(
            "corr_cat_gene_input",
            choices=sh.genes,
            selected=[],
            server=True,
        )

    @reactive.effect
    def _():
        ui.update_selectize(
            "fs_dge_highlight_genes",
            choices=sh.genes,
            selected=[],
            server=True,
        )

    @reactive.effect
    def _():
        ui.update_selectize(
            "dge_highlight_genes",
            choices=sh.genes,
            selected=[],
            server=True,
        )
       

# Create the Shiny app
app = App(app_ui, server)


