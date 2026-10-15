from collections.abc import Iterator

import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def empty_caches() -> Iterator[None]:
    """Start every test with Streamlit's caches empty, as a newly started app has them."""
    st.cache_data.clear()
    st.cache_resource.clear()
    yield
    st.cache_data.clear()
    st.cache_resource.clear()
