import requests
from config import RYOT_GRAPHQL_URL, HEADERS, USER_ID

def get_all_shows():
    """Fetches IDs of all your shows."""
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
            "search": { "page": 1, "take": 500, "query": "" },
            "sort": {"by": "LAST_UPDATED", "order": "DESC"},
            "filter": {"general": "ALL", "collections": [], "dateRange": {}}
        }
    }
    try:
        response = requests.post(RYOT_GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS).json()
        return [{"id": mid} for mid in response.get("data", {}).get("userMetadataList", {}).get("response", {}).get("items", [])]
    except Exception as e:
        print(f"❌ Error connecting to Ryot to list shows: {e}")
        return []

def analyze_show_status(metadata_id):
    """
    Advanced logic: Ignores Specials (S00) and checks Production Status.
    """
    query_meta = """
    query MetadataDetails($metadataId: String!) {
      metadataDetails(metadataId: $metadataId) {
        response {
          title
          productionStatus
          showSpecifics {
            totalSeasons
          }
        }
      }
    }
    """
    query_user = """
    query UserMetadataDetails($metadataId: String!) {
      userMetadataDetails(metadataId: $metadataId) {
        response {
          showProgress {
            seasonNumber
            episodes {
              timesSeen
            }
          }
        }
      }
    }
    """
    
    try:
        res_m = requests.post(RYOT_GRAPHQL_URL, json={"query": query_meta, "variables": {"metadataId": metadata_id}}, headers=HEADERS).json()
        res_u = requests.post(RYOT_GRAPHQL_URL, json={"query": query_user, "variables": {"metadataId": metadata_id}}, headers=HEADERS).json()
        
        meta_data = res_m.get("data", {}).get("metadataDetails", {}).get("response", {})
        user_data = res_u.get("data", {}).get("userMetadataDetails", {}).get("response", {})
        
        title = meta_data.get("title", f"ID: {metadata_id}")
        total_seasons_official = meta_data.get("showSpecifics", {}).get("totalSeasons", 0) or 0
        
        raw_status = meta_data.get("productionStatus")
        production_status = str(raw_status).strip().upper() if raw_status else ""
        
        progress_structure = user_data.get("showProgress", [])
        regular_seasons = [s for s in progress_structure if s.get("seasonNumber", 0) > 0]
        
        seasons_interacted = [s.get("seasonNumber", 0) for s in regular_seasons]
        max_season_viewed = max(seasons_interacted) if seasons_interacted else 0
        
        has_unwatched_episodes = False
        for season in regular_seasons:
            for ep in season.get("episodes", []):
                if ep.get("timesSeen", 0) == 0:
                    has_unwatched_episodes = True
                    break
        
        is_incomplete = False
        reason = ""
        
        if has_unwatched_episodes:
            is_incomplete = True
            reason = "Pending episodes to watch (Ignoring Specials)."
        elif total_seasons_official > max_season_viewed:
            is_incomplete = True
            reason = f"Missing entire seasons (Watched {max_season_viewed} out of {total_seasons_official})."
        elif production_status and production_status not in ["ENDED", "CANCELED", "CANCELLED"]:
            is_incomplete = True
            reason = f"Up to date, but the show is still airing (Status: {production_status})."
        else:
            is_incomplete = False
            reason = "Fully finished and completed."
            
        return title, is_incomplete, reason
        
    except Exception as e:
        print(f"⚠️ Error analyzing show {metadata_id}: {e}")
        return None, False, "Analysis error"

def move_to_watchlist(metadata_id, title):
    """Adds the show to the 'Watchlist' collection."""
    mutation_watchlist = """
    mutation DeployAddEntitiesToCollectionJob($input: ChangeCollectionToEntitiesInput!) {
      deployAddEntitiesToCollectionJob(input: $input)
    }
    """
    variables = {
        "input": {
            "collectionName": "Watchlist",
            "creatorUserId": USER_ID,
            "entities": [{"entityId": metadata_id, "entityLot": "METADATA"}]
        }
    }
    try:
        resp = requests.post(RYOT_GRAPHQL_URL, json={"query": mutation_watchlist, "variables": variables}, headers=HEADERS).json()
        if "errors" in resp:
            print(f"  ❌ API Error while adding to Watchlist: {resp.get('errors')}")
            return False
        else:
            print(f"  📌 [ACTION] Secured in your Watchlist!")
            return True
    except Exception as e:
        print(f"  🔌 Network error for Watchlist in '{title}': {e}")
        return False

def remove_from_watchlist(metadata_id, title):
    """Removes the show from the 'Watchlist' collection if it exists."""
    mutation_remove = """
    mutation DeployRemoveEntitiesFromCollectionJob($input: ChangeCollectionToEntitiesInput!) {
      deployRemoveEntitiesFromCollectionJob(input: $input)
    }
    """
    variables = {
        "input": {
            "collectionName": "Watchlist",
            "creatorUserId": USER_ID,
            "entities": [{"entityId": metadata_id, "entityLot": "METADATA"}]
        }
    }
    try:
        resp = requests.post(RYOT_GRAPHQL_URL, json={"query": mutation_remove, "variables": variables}, headers=HEADERS).json()
        if "errors" in resp:
            return False
        else:
            print(f"  ✨ [ACTION] Preventively removed from Watchlist!")
            return True
    except Exception as e:
        print(f"  🔌 Network error while removing from Watchlist for '{title}': {e}")
        return False

def main():
    print("="*60)
    print("🤖 AUTOMATIC WATCHLIST MANAGER FOR SHOWS (RYOT v10)")
    print("="*60)
    
    shows = get_all_shows()
    if not shows:
        print("❌ No shows found to analyze in your library.")
        return
        
    print(f"📊 Analyzing {len(shows)} shows with smart Watchlist cleanup...\n")
    
    counter_added = 0
    counter_removed = 0
    
    for index, show in enumerate(shows, 1):
        metadata_id = show["id"]
        
        title, is_incomplete, reason = analyze_show_status(metadata_id)
        
        if not title:
            continue
            
        print(f"[{index}/{len(shows)}] 📺 {title}")
        print(f"  ↳ STATUS: {reason}")
        
        if is_incomplete:
            success = move_to_watchlist(metadata_id, title)
            if success:
                counter_added += 1
        else:
            remove_from_watchlist(metadata_id, title)
            counter_removed += 1
            
    print("\n" + "="*60)
    print("🎉 AUTOMATIC PROCESS COMPLETED!")
    print(f"🚀 Shows sent/maintained in Watchlist: {counter_added}")
    print(f"✨ Shows cleaned/excluded from Watchlist: {counter_removed}")
    print("="*60)

if __name__ == "__main__":
    main()