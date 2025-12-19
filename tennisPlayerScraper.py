import requests
from bs4 import BeautifulSoup
import json
import os
from playwright.sync_api import sync_playwright
import time
import re

PLAYERS_DB_FILE = "players_db.json"

def load_players_db():
    """Load saved player URLs from local database"""
    if os.path.exists(PLAYERS_DB_FILE):
        try:
            with open(PLAYERS_DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_players_db(db):
    """Save player URLs to local database"""
    with open(PLAYERS_DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def searchPlayer(name, tour):
    """
    Search for a player using Playwright and return their profile URL.
    This function handles the automatic search on ATP/WTA websites.
    """
    db = load_players_db()
    key = f"{name}_{tour}".lower()
    
    # Check cache first
    if key in db:
        return db[key]
    
    # If not in cache, search the website
    print(f"\n🔍 Searching for {name} on {tour.upper()} website...")
    
    base = "https://www.wtatennis.com" if tour == "wta" else "https://www.atptour.com"
    search_url = f"{base}/search?term={requests.utils.quote(name)}" if tour == "wta" else f"{base}/en/players?search={requests.utils.quote(name)}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except:
                pass
            time.sleep(1)
            
            # Look for player links
            if tour == "wta":
                # WTA uses different selectors
                link = page.query_selector("a.search-result-item")
                if link:
                    href = link.get_attribute("href")
                    player_url = base + href
                    
                    # Cache the result
                    db[key] = player_url
                    save_players_db(db)
                    print(f"✅ Found and cached: {player_url}")
                    return player_url
            else:
                # ATP - find player links with /overview suffix
                links = page.query_selector_all("a[href*='/en/players/'][href*='/overview']")
                
                best_match = None
                name_lower = name.lower()
                
                # Look for best text match
                for link in links:
                    href = link.get_attribute("href")
                    text = link.text_content().strip()
                    text_lower = text.lower()
                    
                    # Look for exact or partial match in text
                    if name_lower in text_lower:
                        best_match = href
                        break
                
                # If no text match, use the first valid player link
                if not best_match and len(links) > 0:
                    best_match = links[0].get_attribute("href")
                
                if best_match:
                    player_url = base + best_match if not best_match.startswith("http") else best_match
                    
                    # Cache the result
                    db[key] = player_url
                    save_players_db(db)
                    print(f"✅ Found and cached: {player_url}")
                    return player_url
            
            print(f"❌ No results found for {name}")
            return None
        except Exception as e:
            print(f"❌ Search error: {e}")
            return None
        finally:
            browser.close()

def fetchOverview(profileUrl):
    """Fetch player overview using Playwright to render JavaScript"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(profileUrl, wait_until="domcontentloaded", timeout=15000)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except:
                pass
            time.sleep(3)  # Give JavaScript time to render stats
            
            # Get both rendered HTML and rendered text
            html = page.content()
            all_text = page.locator("body").text_content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract player name from URL
            try:
                player_slug = profileUrl.split('/players/')[-1]
                player_slug = player_slug.split('/')[0]
                player_name = player_slug.replace('-', ' ').title()
            except:
                player_name = "Unknown"
            
            # Initialize result
            result = {
                "name": player_name,
                "age": "N/A",
                "height": "N/A",
                "weight": "N/A",
                "country": "N/A",
                "rank": "N/A",
                "careerHighRank": "N/A",
                "winLoss": "N/A",
                "seasonWinLoss": "N/A",
                "titles": "N/A"
            }
            
            # Look for data in specific patterns
            text = soup.get_text()
            
            # Extract Age (format: "Age38 (1987/05/22)")
            age_match = re.search(r'Age(\d+)\s*\(', text)
            if age_match:
                result["age"] = age_match.group(1)
            
            # Extract Height (format: "Height6'2\" (188cm)")
            height_match = re.search(r"Height([^(]+)", text)
            if height_match:
                result["height"] = height_match.group(1).strip()
            
            # Extract Weight (format: "Weight170 lbs (77kg)")
            weight_match = re.search(r'Weight([^(]+)', text)
            if weight_match:
                result["weight"] = weight_match.group(1).strip()
            
            # Extract Country (format: "CountrySerbia")
            country_match = re.search(r'Country([A-Z][a-z\s]+)(?:Birthplace|Plays)', text)
            if country_match:
                result["country"] = country_match.group(1).strip()
            
            # Extract Birthplace
            birthplace_match = re.search(r'Birthplace([^P]+?)(?:Plays|Coach)', text)
            if birthplace_match:
                birthplace = birthplace_match.group(1).strip()
                if result["country"] == "N/A":
                    result["country"] = birthplace.split(',')[-1].strip() if ',' in birthplace else birthplace
            
            # Extract Current Rank (from rendered text: "YTD Rank: 4")
            ytd_rank_match = re.search(r'YTD Rank[:\s]+(\d+)', all_text)
            if ytd_rank_match:
                result["rank"] = ytd_rank_match.group(1)
            
            # Extract Career High Rank (from rendered text - format: "1 Career High Rank (2011.07.04)")
            career_high_match = re.search(r'(\d+)\s+Career High Rank', all_text, re.IGNORECASE)
            if career_high_match:
                result["careerHighRank"] = career_high_match.group(1)
            
            # Extract Season Win-Loss record (first match: "39 - 11")
            season_wl_match = re.search(r'YTD.*?(\d+)\s*[-–]\s*(\d+)\s+W-L', all_text, re.IGNORECASE | re.DOTALL)
            if season_wl_match:
                result["seasonWinLoss"] = f"{season_wl_match.group(1)}-{season_wl_match.group(2)}"
            
            # Extract Win-Loss record (Career: "1163 - 233" - appears after Season W-L)
            winloss_pattern = r'(\d+)\s*[-–]\s*(\d+)\s+W-L'
            winloss_matches = list(re.finditer(winloss_pattern, all_text))
            if len(winloss_matches) > 1:  # Use second (career) if available
                result["winLoss"] = f"{winloss_matches[1].group(1)}-{winloss_matches[1].group(2)}"
            elif len(winloss_matches) > 0:
                result["winLoss"] = f"{winloss_matches[0].group(1)}-{winloss_matches[0].group(2)}"
            
            # Extract Titles (Season: first match "2", Career: second match "101")
            titles_pattern = r'(\d+)\s+Title'
            titles_matches = list(re.finditer(titles_pattern, all_text))
            if len(titles_matches) > 1:  # Use second (career) if available
                result["titles"] = titles_matches[1].group(1)
            elif len(titles_matches) > 0:
                result["titles"] = titles_matches[0].group(1)
            
            return result
        finally:
            browser.close()

def fetchPerformance(profileUrl):
    """Fetch performance data using Playwright"""
    return {
        "seasonWL": "N/A",
        "surfaces": {}
    }

def fetchMatches(profileUrl):
    """Fetch recent matches using Playwright"""
    return []

def fetchGrandSlams(profileUrl):
    """Fetch Grand Slam titles using Playwright"""
    return 0

def main():
    print("\n🎾 TENNIS PLAYER SCRAPER")
    print("=" * 50)
    print("\nOptions:")
    print("1. Look up a player (need profile URL)")
    print("2. View cached players")
    print("3. Add new player to cache\n")
    
    choice = input("Choose option (1-3): ").strip()
    
    if choice == "1":
        # Look up a player
        name = input("\nPlayer name: ").strip()
        tour_input = input("Tour (ATP/WTA): ").strip().lower()
        
        if tour_input not in ["atp", "wta"]:
            print("❌ Invalid tour")
            return
        
        # Search for player (checks cache first, then searches website)
        profileUrl = searchPlayer(name, tour_input)
        
        if not profileUrl:
            print(f"❌ Player not found")
            return
        
        # Fetch player data
        print("\n🔍 Fetching player data...")
        print("   (Browser rendering enabled!)\n")
        print("⚠️  NOTE: The ATP website loads stats via JavaScript")
        print("   Visit the profile URL in your browser for full details:\n")
        print(f"   {profileUrl}\n")
        
        try:
            overview = fetchOverview(profileUrl)
            performance = fetchPerformance(profileUrl)
            matches = fetchMatches(profileUrl) if tour_input == "atp" else "N/A"
            
            print("🎾 PLAYER PROFILE")
            print("=" * 50)
            print(f"Name: {overview['name']}")
            print(f"Country: {overview['country']}")
            print(f"Age: {overview['age']}")
            print(f"Height: {overview['height']}")
            print(f"Weight: {overview['weight']}")
            print(f"Current Rank: {overview['rank']}")
            print(f"Career High Rank: {overview['careerHighRank']}")
            print(f"Career Win/Loss: {overview['winLoss']}")
            print(f"Season Win/Loss: {overview['seasonWinLoss']}")
            print(f"Titles: {overview['titles']}")
            print("\n📊 Surface Records")
            if performance['surfaces']:
                for surface, record in performance['surfaces'].items():
                    print(f"{surface}: {record}")
            else:
                print("(Not available)")
            print("\n🕒 Recent Matches")
            if matches:
                for i, m in enumerate(matches):
                    print(f"{i+1}. {m['tournament']} | {m['round']} | vs {m['opponent']} | {m['result']}")
            else:
                print("(Not available)")
            print("=" * 50)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    elif choice == "2":
        # View cached players
        db = load_players_db()
        if not db:
            print("\n📭 No players cached yet")
        else:
            print("\n📋 Cached Players:")
            print("=" * 50)
            for key, url in sorted(db.items()):
                name, tour = key.rsplit('_', 1)
                print(f"{name.title()} ({tour.upper()}): {url}")
            print("=" * 50)
    
    elif choice == "3":
        # Add new player (auto-search)
        name = input("\nPlayer name: ").strip()
        tour_input = input("Tour (ATP/WTA): ").strip().lower()
        
        if tour_input not in ["atp", "wta"]:
            print("❌ Invalid tour")
            return
        
        # Auto-search for the player
        profileUrl = searchPlayer(name, tour_input)
        
        if profileUrl:
            print(f"\n✅ Player added to cache!")
        else:
            print(f"\n❌ Could not find player. Try a different name or visit the website manually.")
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
