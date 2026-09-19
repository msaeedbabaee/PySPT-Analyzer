import math
import matplotlib.pyplot as plt
import streamlit as st

# Set Streamlit Page Config
st.set_page_config(page_title="GeoSPT-Log", layout="wide")


class SPTAnalyzer:

    def __init__(
        self,
        hammer_efficiency=60,
        borehole_diam_mm=100,
        sampler_has_liner=False,
    ):
        self.hammer_efficiency = hammer_efficiency
        self.borehole_diam_mm = borehole_diam_mm
        self.sampler_has_liner = sampler_has_liner

    def _get_corrections(self, N_field, depth, unit_weight, water_table=None):
        if water_table is not None and depth > water_table:
            dry_depth = water_table
            submerged_depth = depth - water_table
            effective_stress = (dry_depth * unit_weight) + (
                submerged_depth * (unit_weight - 9.81)
            )
        else:
            effective_stress = depth * unit_weight

        if effective_stress < 10.0:
            effective_stress = 10.0

        C_E = self.hammer_efficiency / 60.0

        if self.borehole_diam_mm <= 115:
            C_B = 1.0
        elif self.borehole_diam_mm <= 150:
            C_B = 1.05
        else:
            C_B = 1.15

        C_S = 1.2 if self.sampler_has_liner else 1.0

        if depth < 3.0:
            C_R = 0.75
        elif 3.0 <= depth < 4.0:
            C_R = 0.85
        elif 4.0 <= depth < 6.0:
            C_R = 0.95
        else:
            C_R = 1.0

        N60 = N_field * C_E * C_B * C_S * C_R

        Pa = 100.0
        C_N = math.sqrt(Pa / effective_stress)
        if C_N > 1.7:
            C_N = 1.7

        N1_60 = N60 * C_N

        return {
            "N_field": N_field,
            "N60": round(N60, 2),
            "N1_60": round(N1_60, 2),
            "effective_stress_kPa": round(effective_stress, 2),
            "C_N": round(C_N, 2),
        }

    def evaluate_layer(
        self, soil_type, N_field, depth, unit_weight=18.0, water_table=None
    ):
        corr = self._get_corrections(N_field, depth, unit_weight, water_table)

        if soil_type.lower() == "cohesive":
            N_eval = corr["N60"]
            if N_eval < 2:
                consistency, cu_min, cu_max = "Very Soft", 0.0, 12.5
            elif 2 <= N_eval < 4:
                consistency, cu_min, cu_max = "Soft", 12.5, 25.0
            elif 4 <= N_eval < 8:
                consistency, cu_min, cu_max = "Firm", 25.0, 50.0
            elif 8 <= N_eval < 15:
                consistency, cu_min, cu_max = "Stiff", 50.0, 100.0
            elif 15 <= N_eval <= 30:
                consistency, cu_min, cu_max = "Very Stiff", 100.0, 200.0
            else:
                consistency, cu_min, cu_max = "Hard", 200.0, 300.0

            result = {
                "depth": depth,
                "soil_type": "Cohesive",
                "classification": consistency,
                "cu_min_kPa": cu_min,
                "cu_max_kPa": cu_max,
                "cu_avg_kPa": (cu_min + cu_max) / 2.0,
            }

        elif soil_type.lower() == "cohesionless":
            N_eval = corr["N1_60"]
            if N_eval < 4:
                compactness, phi_min, phi_max, dr_min, dr_max = (
                    "Very Loose",
                    25.0,
                    28.0,
                    0,
                    15,
                )
            elif 4 <= N_eval < 10:
                compactness, phi_min, phi_max, dr_min, dr_max = (
                    "Loose",
                    28.0,
                    30.0,
                    15,
                    35,
                )
            elif 10 <= N_eval < 30:
                compactness, phi_min, phi_max, dr_min, dr_max = (
                    "Medium Dense",
                    30.0,
                    36.0,
                    35,
                    65,
                )
            elif 30 <= N_eval <= 50:
                compactness, phi_min, phi_max, dr_min, dr_max = (
                    "Dense",
                    36.0,
                    41.0,
                    65,
                    85,
                )
            else:
                compactness, phi_min, phi_max, dr_min, dr_max = (
                    "Very Dense",
                    41.0,
                    45.0,
                    85,
                    100,
                )

            result = {
                "depth": depth,
                "soil_type": "Cohesionless",
                "classification": compactness,
                "phi_avg_deg": (phi_min + phi_max) / 2.0,
                "relative_density_avg_%": (dr_min + dr_max) / 2.0,
            }

        result.update(corr)
        return result

    def get_borehole_figure(self, borehole_data, water_table=None):
        depths = [item["depth"] for item in borehole_data]
        n_fields = [item["N_field"] for item in borehole_data]
        n60s = [item["N60"] for item in borehole_data]
        n1_60s = [item["N1_60"] for item in borehole_data]

        fig, axs = plt.subplots(1, 3, figsize=(14, 7), sharey=True)
        fig.suptitle(
            "Geotechnical Borehole Log & SPT Analysis",
            fontsize=16,
            fontweight="bold",
        )

        # Plot 1: SPT Profiles
        axs[0].plot(n_fields, depths, "o--k", label="N_field")
        axs[0].plot(n60s, depths, "s-b", label="N60")
        axs[0].plot(n1_60s, depths, "^-r", label="(N1)60")
        axs[0].set_xlabel("SPT N-Value", fontweight="bold")
        axs[0].set_ylabel("Depth (m)", fontweight="bold")
        axs[0].set_title("SPT Values vs Depth")
        axs[0].grid(True, linestyle="--", alpha=0.6)
        axs[0].legend()

        # Plot 2: Cohesive Strength
        cu_depths = [
            item["depth"]
            for item in borehole_data
            if item["soil_type"] == "Cohesive"
        ]
        cu_vals = [
            item["cu_avg_kPa"]
            for item in borehole_data
            if item["soil_type"] == "Cohesive"
        ]
        if cu_depths:
            axs[1].plot(cu_vals, cu_depths, "s-purple", label="cu (kPa)")
            axs[1].set_xlabel(
                "Undrained Shear Strength cu (kPa)", fontweight="bold"
            )
            axs[1].set_title("Cohesive Layers")
            axs[1].grid(True, linestyle="--", alpha=0.6)
            axs[1].legend()

        # Plot 3: Friction Angle
        phi_depths = [
            item["depth"]
            for item in borehole_data
            if item["soil_type"] == "Cohesionless"
        ]
        phi_vals = [
            item["phi_avg_deg"]
            for item in borehole_data
            if item["soil_type"] == "Cohesionless"
        ]
        if phi_depths:
            axs[2].plot(
                phi_vals, phi_depths, "d-green", label="Friction Angle φ (°)"
            )
            axs[2].set_xlabel(
                "Friction Angle φ (degrees)", fontweight="bold"
            )
            axs[2].set_title("Cohesionless Layers")
            axs[2].grid(True, linestyle="--", alpha=0.6)
            axs[2].legend()

        plt.gca().invert_yaxis()

        if water_table is not None:
            for ax in axs:
                ax.axhline(
                    y=water_table,
                    color="cyan",
                    linestyle=":",
                    linewidth=2,
                    label="Water Table",
                )

        plt.tight_layout()
        return fig


# Streamlit Web UI
st.title("🌋 GeoSPT-Log: Geotechnical SPT N-Value Analyzer")

st.sidebar.header("Equipment Parameters")
hammer_eff = st.sidebar.slider("Hammer Efficiency (%)", 40, 90, 70)
borehole_diam = st.sidebar.selectbox(
    "Borehole Diameter (mm)", [100, 115, 150, 200]
)
has_liner = st.sidebar.checkbox("Sampler Has Liner", False)
water_table_depth = st.sidebar.number_input(
    "Water Table Depth (m)", value=2.5, step=0.5
)

st.write("### Simulated Borehole Input Data")

analyzer = SPTAnalyzer(
    hammer_efficiency=hammer_eff,
    borehole_diam_mm=borehole_diam,
    sampler_has_liner=has_liner,
)

raw_borehole_data = [
    {"soil_type": "cohesive", "N_field": 3, "depth": 1.5, "unit_weight": 17.5},
    {"soil_type": "cohesive", "N_field": 6, "depth": 3.0, "unit_weight": 18.0},
    {
        "soil_type": "cohesionless",
        "N_field": 14,
        "depth": 4.5,
        "unit_weight": 18.5,
    },
    {
        "soil_type": "cohesionless",
        "N_field": 22,
        "depth": 6.0,
        "unit_weight": 19.0,
    },
    {
        "soil_type": "cohesionless",
        "N_field": 35,
        "depth": 7.5,
        "unit_weight": 19.5,
    },
    {"soil_type": "cohesive", "N_field": 18, "depth": 9.0, "unit_weight": 18.5},
]

processed_results = []
for layer in raw_borehole_data:
    res = analyzer.evaluate_layer(
        soil_type=layer["soil_type"],
        N_field=layer["N_field"],
        depth=layer["depth"],
        unit_weight=layer["unit_weight"],
        water_table=water_table_depth,
    )
    processed_results.append(res)

st.dataframe(processed_results)

st.write("### Depth Profile Visual Log")
fig = analyzer.get_borehole_figure(
    processed_results, water_table=water_table_depth
)
st.pyplot(fig)
