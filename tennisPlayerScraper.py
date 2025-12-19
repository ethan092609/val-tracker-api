import requests
from bs4 import BeautifulSoup

def searchPlayer(name, tour):
    base = "https://www.wtatennis.com" if tour == "wta" else "https://www.atptour.com"
    searchUrl = f"{base}/search?term={requests.utils.quote(name)}" if tour == "wta" else f"{base}/en/players?search={requests.utils.quote(name)}"
    response = requests.get(searchUrl)
    soup = BeautifulSoup(response.text, 'html.parser')
    link = soup.select_one("a.search-result-item")
    if not link:
        return None
    return base + link['href']

def fetchOverview(profileUrl):
    response = requests.get(profileUrl)
    soup = BeautifulSoup(response.text, 'html.parser')
    name = soup.select_one("h1").text.strip()
    bio = {}
    for tr in soup.select(".player-profile-hero-table tr"):
        label = tr.select_one("th").text.strip()
        value = tr.select_one("td").text.strip()
        bio[label] = value
    stats = {}
    for tr in soup.select(".player-profile-stat-table tr"):
        label = tr.select_one("th").text.strip()
        value = tr.select_one("td").text.strip()
        stats[label] = value
    return {
        "name": name,
        "age": bio.get("Age"),
        "height": bio.get("Height"),
        "weight": bio.get("Weight"),
        "country": bio.get("Country"),
        "rank": stats.get("Rank"),
        "careerHighRank": stats.get("Career High Rank"),
        "winLoss": stats.get("Win/Loss"),
        "titles": stats.get("Titles")
    }

def fetchPerformance(profileUrl):
    url = profileUrl.replace("/overview", "/performance")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    seasonWL = soup.select_one(".performance-season-record").text.strip()
    surfaces = {}
    for tr in soup.select(".surface-breakdown tr"):
        surface = tr.select_one("th").text.strip()
        record = tr.select_one("td").text.strip()
        if surface:
            surfaces[surface] = record
    return {"seasonWL": seasonWL, "surfaces": surfaces}

def fetchMatches(profileUrl):
    url = profileUrl.replace("/overview", "/matches")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    matches = []
    for el in soup.select(".match-row")[:5]:
        matches.append({
            "tournament": el.select_one(".tourney-title").text.strip(),
            "round": el.select_one(".round").text.strip(),
            "opponent": el.select_one(".opponent-name").text.strip(),
            "result": el.select_one(".score").text.strip()
        })
    return matches

def fetchGrandSlams(profileUrl):
    url = profileUrl.replace("/overview", "/titles-and-finals")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    slams = len(soup.select(".tournament-type-grand-slam"))
    return slams

def main():
    name = input("Search player name: ")
    tour_input = input("Tour (ATP/WTA): ")
    tour = tour_input.lower()
    if tour not in ["atp", "wta"]:
        print("❌ Invalid tour.")
        return
    print("\n🔍 Searching...")
    profileUrl = searchPlayer(name, tour)
    if not profileUrl:
        print("❌ Player not found.")
        return
    overview = fetchOverview(profileUrl)
    performance = fetchPerformance(profileUrl)
    matches = fetchMatches(profileUrl)
    slams = fetchGrandSlams(profileUrl) if tour == "atp" else "N/A"
    print("\n🎾 PLAYER PROFILE")
    print("--------------------------------------------------")
    print(f"Name: {overview['name']}")
    print(f"Country: {overview['country']}")
    print(f"Age: {overview['age']}")
    print(f"Height: {overview['height']}")
    print(f"Weight: {overview['weight']}")
    print(f"Current Rank: {overview['rank']}")
    print(f"Career High Rank: {overview['careerHighRank']}")
    print(f"Career Win/Loss: {overview['winLoss']}")
    print(f"Season Win/Loss: {performance['seasonWL']}")
    print(f"Titles: {overview['titles']}")
    print(f"Grand Slams: {slams}")
    print("\n📊 Surface Records")
    for surface, record in performance['surfaces'].items():
        print(f"{surface}: {record}")
    print("\n🕒 Recent Matches")
    for i, m in enumerate(matches):
        print(f"{i+1}. {m['tournament']} | {m['round']} | vs {m['opponent']} | {m['result']}")
    print("--------------------------------------------------")

if __name__ == "__main__":
    main()