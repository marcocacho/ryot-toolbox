# Ryot Library Tools (v10)

A set of Python scripts to automate, import, and manage your Movies and TV Shows library on your self-hosted **Ryot** (v10+) server using its GraphQL API.

## 📁 File Structure

* `config.py`: Centralized configuration file holding your API credentials and endpoints. Review `config.example.py`
* `import_imdb_to_ryot.py`: Imports ratings and watch history from an IMDb CSV export. If you’d already marked it as read, it adds a second one
* `import_shows.py`: CLI interactive utility to mark TV Show season progress in bulk.
* `auto_watchlist_shows.py`: Automates your "Watchlist" collection dynamically according to show production and personal watch statuses.

## The Motivation (Why this exists)

When importing history into Ryot, native tools sometimes map items strictly into the pending watchlist instead of marking them as historically viewed or migrating user ratings. These scripts solve this limitation by matching your IMDb CSV export against your pre-existing library metadata, applying bulk episode watch history via GraphQL mutations, and fixing review scores seamlessly.

---

## ⚙️ Setup Instructions

### 1. Requirements
Ensure you have Python 3 and the `requests` library installed.


### 2. Configuration

Copy the config.example.py file to a new file named config.py and set your credentials:

* RYOT_GRAPHQL_URL: The GraphQL URL backend of your Ryot instance (e.g., https://your-domain.com/backend/graphql).

* API_TOKEN: Your Ryot API Bearer Token.

* USER_ID: Your Ryot user identifier string (usr_...).

* CSV_FILE_PATH: The name/path of your exported IMDb ratings file (default: ratings.csv).

---

## 🚀 Script Features & Usage

### 1. IMDb History Import

File: `import_imdb_to_ryot.py`

Matches items inside your ratings.csv export with your current Ryot local library. It updates the media as "Seen" matching the original date from IMDb and applies your review scores (converting IMDb's 1–10 scale into Ryot's 1–100% scale).

```bash
python import_imdb_to_ryot.py
```

### 2. Interactive TV Show Progress Manager

File: `import_shows.py`

Fetches all your tracked shows in Ryot and parses them through an interactive terminal menu. It extracts historical dates from the CSV if available. For each show, you can:

* Mark the entire show as watched (100% completion).

* Specify up to which season you have watched (marking all previous episodes as completed while leaving the remaining seasons untouched).

* Skip the show.

```bash
python import_shows.py
```

### 3. Automated Watchlist Manager

File: `auto_watchlist_shows.py`

Scans your entire TV show library to run a smart evaluation algorithm. It ignores Special/Bonus seasons (Season 0) and modifies the "Watchlist" collection dynamically:

* Adds to Watchlist if you have pending episodes, missing full seasons, or if you are up-to-date but the show's production status is still ongoing (Returning Series, In Production, etc.).

* Removes from Watchlist preventively if the series is fully finished (Ended, Canceled) and you have completed every episode.

```bash
python auto_watchlist_shows.py
```

## ⚠️ Important Notes

* Make sure your media is already added or mapped in Ryot before running the import scripts, as they look for pre-existing metadataId matches.

* The scripts include a slight built-in delay (time.sleep) to prevent hitting rate limits on your host server.