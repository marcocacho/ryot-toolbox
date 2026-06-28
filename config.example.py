# config.py

# ==========================================
# ⚙️ GLOBAL CONFIGURATION
# ==========================================
RYOT_GRAPHQL_URL = "URL|IP:port/backend/graphql" # <-- Replace with your url
API_TOKEN = "asdfasdfasdf===="  # <-- Replace with your real API token
USER_ID = "usr_xxxxx"        # <-- Replace with your real User ID
CSV_FILE_PATH = "ratings.csv" # <-- Replace with your IMDB download

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}