import pprint
from streamlit.source_util import get_pages

# Print pages registered for src/app.py
pages = get_pages("src/app.py")
pprint.pprint(pages)
