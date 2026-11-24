"""Pembuat grafik Plotly yang tidak bergantung pada Streamlit."""

import plotly.graph_objects as go

from nutrikos.core import energi_makro


def grafik_makro(total: dict[str, float]) -> go.Figure:
    """Membuat diagram donat kontribusi energi makro menggunakan faktor 4/4/9."""
    energi = energi_makro(total)
    gambar = go.Figure(go.Pie(labels=list(energi), values=list(energi.values()), hole=0.55,
                              marker_colors=["#3688A1", "#3BA382", "#E2A64B"],
                              textinfo="label+percent", hovertemplate="%{label}: %{value:.1f} kkal<extra></extra>"))
    gambar.update_layout(title="Proporsi energi dari makronutrisi", height=380,
                         margin=dict(t=60, b=20, l=20, r=20))
    return gambar


def grafik_target(total: dict[str, float], target: dict[str, float]) -> go.Figure:
    """Membandingkan gram makro; kalori ditampilkan terpisah agar satuan tidak bercampur."""
    gambar = go.Figure()
    label = ["Karbohidrat", "Protein", "Lemak"]
    gambar.add_bar(name="Target model", x=label,
                   y=[target["target_karbo_g"], target["target_protein_g"], target["target_lemak_g"]],
                   marker_color="#CBD5E1")
    gambar.add_bar(name="Asupan tercatat", x=label,
                   y=[total["karbo_gram"], total["protein_gram"], total["lemak_gram"]],
                   marker_color="#23856D")
    gambar.update_layout(title="Makro vs target profil saat ini", barmode="group",
                         yaxis_title="Gram", height=380, margin=dict(t=60, b=20, l=30, r=20))
    return gambar
