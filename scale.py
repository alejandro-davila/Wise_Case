"""One shared multiplier: turns the 10,000-record sample into PartnerBank's full size.

Only counts and money totals are multiplied when shown. Shares, rates and
per-transfer amounts never change, so every percentage stays the same.
"""
FACTOR = 20   # Jan–Mar 2026: 1,608 sample fee checks vs 33,000 in the QBR deck (×20.5, rounded)
S = 1         # set by app.py from the sidebar switch


def n(x):
    """Scale a count and round it to a whole number."""
    return int(round(x * S))


def money(x):
    """Scale a money total."""
    return x * S


INTERNAL = False  # True = Wise team view (shows Wise revenue); False = partner view


def wise_tag(note='Wise team only'):
    """Small yellow tag; a bordered container holding it gets a yellow frame (CSS in app.py)."""
    import streamlit as st
    st.markdown(f'<span class="wise-only-tag">🔒 {note}</span>', unsafe_allow_html=True)
