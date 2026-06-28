import csv
import requests
from datetime import datetime
import time
from config import RYOT_GRAPHQL_URL, HEADERS, CSV_FILE_PATH

def _execute_search(query_str, lot_type):
    """Helper function to search content via API."""
    query = """
    query UserMetadataList($input: UserMetadataListInput!) {
      userMetadataList(input: $input) {
        response {
          items
        }
      }
    }
    """
    variables = {
        "input": {
            "lot": lot_type,
            "search": {
                "page": 1,
                "query": query_str
            },
            "sort": {"by": "LAST_UPDATED", "order": "DESC"},
            "filter": {"general": "ALL", "collections": [], "dateRange": {}}
        }
    }
    
    payload = {"query": query, "variables": variables, "operationName": "UserMetadataList"}
    
    try:
        response = requests.post(RYOT_GRAPHQL_URL, json=payload, headers=HEADERS)
        items = response.json().get("data", {}).get("userMetadataList", {}).get("response", {}).get("items", [])
        return items[0] if items else None
    except Exception:
        return None

def get_ryot_metadata_id(title, title_type):
    """
    Intelligently searches for media in your local library.
    """
    is_show = title_type and "tv" in title_type.lower()
    search_order = ["SHOW", "MOVIE"] if is_show else ["MOVIE", "SHOW"]
    
    # Attempt 1: Exact title match
    for lot in search_order:
        result = _execute_search(title, lot)
        if result: 
            return result
        
    # Attempt 2: If title contains a colon (":"), search using only the first part
    if ":" in title:
        short_title = title.split(":")[0].strip()
        for lot in search_order:
            result = _execute_search(short_title, lot)
            if result: 
                return result
            
    return None

def update_media_in_ryot(metadata_id, title, rating, date_rated, title_type):
    """
    Applies progress (mark as seen) and adds a review using EntityLot: METADATA.
    """
    try:
        date_obj = datetime.strptime(date_rated, "%Y-%m-%d")
        iso_date = date_obj.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except ValueError:
        iso_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")

    # ==========================================
    # ACTION 1: Mark as Seen (Progress)
    # ==========================================
    mutation_progress = """
    mutation DeployBulkMetadataProgressUpdate($input: [MetadataProgressUpdateInput!]!) {
      deployBulkMetadataProgressUpdate(input: $input)
    }
    """
    
    variables_progress = {
        "input": [{
            "metadataId": metadata_id,
            "change": {
                "createNewCompleted": {
                    "finishedOnDate": {
                        "providersConsumedOn": [],
                        "timestamp": iso_date
                    }
                }
            }
        }]
    }

    payload_progress = {
        "query": mutation_progress,
        "variables": variables_progress,
        "operationName": "DeployBulkMetadataProgressUpdate"
    }

    try:
        resp_prog = requests.post(RYOT_GRAPHQL_URL, json=payload_progress, headers=HEADERS)
        res_prog = resp_prog.json()
        
        if resp_prog.status_code == 200 and "errors" not in res_prog:
            status_msg = f"✅ Success: '{title}' marked as seen."
            
            # ==========================================
            # ACTION 2: Rate Media (Review)
            # ==========================================
            if rating:
                mutation_review = """
                mutation CreateOrUpdateReview($input: CreateOrUpdateReviewInput!) {
                  createOrUpdateReview(input: $input) {
                    id
                  }
                }
                """
                
                # IMDb uses a 1-10 scale. Ryot uses a 1-100 (%) scale.
                corrected_rating = float(rating) * 10.0
                
                variables_review = {
                    "input": {
                        "entityId": metadata_id,
                        "entityLot": "METADATA",
                        "rating": corrected_rating
                    }
                }
                
                payload_review = {
                    "query": mutation_review,
                    "variables": variables_review,
                    "operationName": "CreateOrUpdateReview"
                }
                
                resp_rev = requests.post(RYOT_GRAPHQL_URL, json=payload_review, headers=HEADERS)
                res_rev = resp_rev.json()
                
                if resp_rev.status_code == 200 and "errors" not in res_rev:
                    status_msg += f" (🌟 Rating applied: {corrected_rating}%)"
                else:
                    status_msg += f" (⚠️ Marked as seen, but rating failed: {res_rev.get('errors')})"
                    
            print(status_msg)
            
        else:
            print(f"❌ Error marking '{title}' as seen: {res_prog.get('errors')}")
            
    except Exception as e:
        print(f"🔌 Connection error for '{title}': {e}")

def main():
    print("Starting advanced import (Shows & Movies) to Ryot v10...")
    
    try:
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            
            for row in reader:
                title = row.get("Title")
                rating = row.get("Your Rating")
                date_rated = row.get("Date Rated")
                title_type = row.get("Title Type")
                
                if not title:
                    continue
                
                print(f"Searching for: {title}...")
                
                metadata_id = get_ryot_metadata_id(title, title_type)
                
                if metadata_id:
                    update_media_in_ryot(metadata_id, title, rating, date_rated, title_type)
                else:
                    print(f"⚠️ Skipped: Could not find '{title}' in Movies or TV Shows.")
                
                time.sleep(0.3)
                
        print("🎉 Import completed successfully!")
        
    except FileNotFoundError:
        print(f"🚨 Could not find file: {CSV_FILE_PATH}")

if __name__ == "__main__":
    main()