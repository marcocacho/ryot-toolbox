import csv
import requests
from datetime import datetime
from config import RYOT_GRAPHQL_URL, HEADERS, CSV_FILE_PATH

def load_dates_from_csv():
    """Reads the IMDb CSV and maps titles with their rating dates."""
    dates_map = {}
    try:
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                title = row.get("Title")
                date_rated = row.get("Date Rated")
                
                if title and date_rated:
                    title_lower = title.lower().strip()
                    dates_map[title_lower] = date_rated
                    count += 1
                    if ":" in title_lower:
                        dates_map[title_lower.split(":")[0].strip()] = date_rated
            print(f"🔍 [CSV] Mapped {count} historical dates from the CSV file.")
    except FileNotFoundError:
        print(f"⚠️ '{CSV_FILE_PATH}' not found. Defaulting to today's date.")
    return dates_map

def get_all_shows():
    """Downloads all shows using the 'take' parameter discovered via Altair."""
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
            "lot": "SHOW",
            "search": {
                "page": 1, 
                "take": 500,
                "query": ""
            },
            "sort": {"by": "LAST_UPDATED", "order": "DESC"},
            "filter": {"general": "ALL", "collections": [], "dateRange": {}}
        }
    }
    try:
        print("📡 [API] Requesting complete show list from Ryot...")
        response = requests.post(RYOT_GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res_json = response.json()
        if "errors" in res_json:
            print(f"❌ Error listing shows: {res_json['errors']}")
            return []
        item_ids = res_json.get("data", {}).get("userMetadataList", {}).get("response", {}).get("items", [])
        return [{"id": mid} for mid in item_ids]
    except Exception as e:
        print(f"❌ Exception while listing shows: {e}")
        return []

def get_show_structure(metadata_id):
    """Fetches real title and episode progress using cross-queries."""
    query_title = """
    query MetadataDetails($metadataId: String!) {
      metadataDetails(metadataId: $metadataId) {
        response {
          title
        }
      }
    }
    """
    query_progress = """
    query UserMetadataDetails($metadataId: String!) {
      userMetadataDetails(metadataId: $metadataId) {
        response {
          showProgress {
            seasonNumber
            episodes {
              episodeNumber
              timesSeen
            }
          }
        }
      }
    }
    """
    
    show_title = f"ID: {metadata_id}"
    show_progress = []
    
    try:
        resp_t = requests.post(RYOT_GRAPHQL_URL, json={"query": query_title, "variables": {"metadataId": metadata_id}}, headers=HEADERS).json()
        show_title = resp_t.get("data", {}).get("metadataDetails", {}).get("response", {}).get("title", show_title)
        
        resp_p = requests.post(RYOT_GRAPHQL_URL, json={"query": query_progress, "variables": {"metadataId": metadata_id}}, headers=HEADERS).json()
        show_progress = resp_p.get("data", {}).get("userMetadataDetails", {}).get("response", {}).get("showProgress", [])
        
    except Exception as e:
        print(f"⚠️ Error resolving details for {metadata_id}: {e}")
        
    return show_title, show_progress

def apply_bulk_progress(metadata_id, title, actions_list):
    """Sends the episode package to the Ryot database."""
    if not actions_list:
        print(f"✅ '{title}' is already up to date. No changes required.")
        return

    mutation_progress = """
    mutation DeployBulkMetadataProgressUpdate($input: [MetadataProgressUpdateInput!]!) {
      deployBulkMetadataProgressUpdate(input: $input)
    }
    """
    payload = {
        "query": mutation_progress,
        "variables": {"input": actions_list},
        "operationName": "DeployBulkMetadataProgressUpdate"
    }
    try:
        resp = requests.post(RYOT_GRAPHQL_URL, json=payload, headers=HEADERS).json()
        if "errors" in resp:
            print(f"❌ API Error on '{title}': {resp.get('errors')}")
            return
        print(f"🚀 [API] Progress saved! {len(actions_list)} new episodes applied to '{title}'.")
    except Exception as e:
        print(f"🔌 Network error while applying progress: {e}")

def main():
    print("="*50)
    print("🎬 INTERACTIVE SHOW PROGRESS MANAGER (RYOT v10)")
    print("="*50)
    
    csv_dates = load_dates_from_csv()
    shows = get_all_shows()
    
    if not shows:
        print("❌ No shows found to process.")
        return
        
    print(f"\n📊 Total shows detected in Ryot: {len(shows)}")
    print("Starting interactive review...\n")
    
    for show in shows:
        metadata_id = show["id"]
        real_title, structure = get_show_structure(metadata_id)
        
        if not structure:
            print(f"⏩ Skipping '{real_title}': Could not read season structure.")
            continue
            
        title_lower = real_title.lower().strip()
        date_rated = csv_dates.get(title_lower)
        if not date_rated and ":" in title_lower:
            date_rated = csv_dates.get(title_lower.split(":")[0].strip())
            
        if date_rated:
            try:
                iso_date = datetime.strptime(date_rated, "%Y-%m-%d").strftime("%Y-%m-%dT%H:%M:%S+00:00")
                display_date = f"{date_rated} (From IMDb)"
            except ValueError:
                iso_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
                display_date = "Today (Incorrect format)"
        else:
            iso_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
            display_date = "Today (Not found in CSV)"
            
        print("\n" + "="*60)
        print(f"📺 SHOW: {real_title}")
        print(f"📅 Planned watch date: {display_date}")
        print("-"*60)
        print("Current status on your server:")
        
        for temp in sorted(structure, key=lambda x: x.get("seasonNumber", 0)):
            s_num = temp.get("seasonNumber")
            watched = sum(1 for e in temp.get("episodes", []) if e.get("timesSeen", 0) > 0)
            total = len(temp.get("episodes", []))
            print(f"  • Season {s_num}: {watched}/{total} episodes watched.")
        print("-"*60)
        
        print("[1] Watched entirely (Mark all seasons as 100% completed)")
        print("[2] Incomplete (Choose up to which season you have watched)")
        print("[3] Not started / Skip")
        
        while True:
            option = input("\n👉 Choose an option (1/2/3): ").strip()
            
            if option in ["1", "2"]:
                max_season = 999
                
                if option == "2":
                    seasons_avail = sorted([s["seasonNumber"] for s in structure if s["seasonNumber"] > 0])
                    try:
                        max_season = int(input(f"Up to which COMPLETED season have you watched? {seasons_avail}: ").strip())
                    except ValueError:
                        print("⚠️ Invalid entry. Canceling selection.")
                        break
                        
                actions_list = []
                for season in structure:
                    s_num = season.get("seasonNumber")
                    
                    if s_num == 0 or s_num > max_season:
                        continue
                        
                    for ep in season.get("episodes", []):
                        times_seen = ep.get("timesSeen", 0)
                        ep_num = ep.get("episodeNumber")
                        
                        if times_seen == 0:
                            actions_list.append({
                                "metadataId": metadata_id,
                                "change": {
                                    "createNewCompleted": {
                                        "finishedOnDate": {
                                            "showSeasonNumber": s_num,
                                            "showEpisodeNumber": ep_num,
                                            "providersConsumedOn": [],
                                            "timestamp": iso_date
                                        }
                                    }
                                }
                            })
                
                apply_bulk_progress(metadata_id, real_title, actions_list)
                break
                
            elif option == "3":
                print("⏩ Show skipped.")
                break
            else:
                print("❌ Invalid option. Please type 1, 2, or 3.")

    print("\n🎉 Library management completed!")

if __name__ == "__main__":
    main()