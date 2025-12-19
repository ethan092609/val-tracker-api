import axios from "axios";
import * as cheerio from "cheerio";
import readline from "readline";

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

async function searchPlayer(name, tour) {
  const base = tour === "wta" ? "https://www.wtatennis.com" : "https://www.atptour.com";
  const searchUrl = tour === "wta" 
    ? `${base}/search?term=${encodeURIComponent(name)}`
    : `${base}/en/players?search=${encodeURIComponent(name)}`;
  const { data } = await axios.get(searchUrl);
  const $ = cheerio.load(data);

  const link = $("a.search-result-item").first().attr("href");
  if (!link) return null;

  return base + link;
}

async function fetchOverview(profileUrl) {
  const { data } = await axios.get(profileUrl);
  const $ = cheerio.load(data);

  const name = $("h1").first().text().trim();

  const bio = {};
  $(".player-profile-hero-table tr").each((_, el) => {
    const label = $(el).find("th").text().trim();
    const value = $(el).find("td").text().trim();
    bio[label] = value;
  });

  const stats = {};
  $(".player-profile-stat-table tr").each((_, el) => {
    const label = $(el).find("th").text().trim();
    const value = $(el).find("td").text().trim();
    stats[label] = value;
  });

  return {
    name,
    age: bio.Age,
    height: bio.Height,
    weight: bio.Weight,
    country: bio.Country,
    rank: stats.Rank,
    careerHighRank: stats["Career High Rank"],
    winLoss: stats["Win/Loss"],
    titles: stats.Titles
  };
}

async function fetchPerformance(profileUrl) {
  const url = profileUrl.replace("/overview", "/performance");
  const { data } = await axios.get(url);
  const $ = cheerio.load(data);

  const seasonWL = $(".performance-season-record").first().text().trim();

  const surfaces = {};
  $(".surface-breakdown tr").each((_, el) => {
    const surface = $(el).find("th").text().trim();
    const record = $(el).find("td").text().trim();
    if (surface) surfaces[surface] = record;
  });

  return { seasonWL, surfaces };
}

async function fetchMatches(profileUrl) {
  const url = profileUrl.replace("/overview", "/matches");
  const { data } = await axios.get(url);
  const $ = cheerio.load(data);

  const matches = [];
  $(".match-row").slice(0, 5).each((_, el) => {
    matches.push({
      tournament: $(el).find(".tourney-title").text().trim(),
      round: $(el).find(".round").text().trim(),
      opponent: $(el).find(".opponent-name").text().trim(),
      result: $(el).find(".score").text().trim()
    });
  });

  return matches;
}

async function fetchGrandSlams(profileUrl) {
  const url = profileUrl.replace("/overview", "/titles-and-finals");
  const { data } = await axios.get(url);
  const $ = cheerio.load(data);

  let slams = 0;
  $(".tournament-type-grand-slam").each(() => slams++);
  return slams;
}

async function main() {
  rl.question("Search player name: ", async (name) => {
    rl.question("Tour (ATP/WTA): ", async (tourInput) => {
      const tour = tourInput.toLowerCase();
      if (!["atp", "wta"].includes(tour)) {
        console.log("❌ Invalid tour.");
        rl.close();
        return;
      }

      console.log("\n🔍 Searching...");
      const profileUrl = await searchPlayer(name, tour);

      if (!profileUrl) {
        console.log("❌ Player not found.");
        rl.close();
        return;
      }

      const overview = await fetchOverview(profileUrl);
      const performance = await fetchPerformance(profileUrl);
      const matches = await fetchMatches(profileUrl);
      const slams = tour === "atp" ? await fetchGrandSlams(profileUrl) : "N/A";

      console.log("\n🎾 PLAYER PROFILE");
      console.log("--------------------------------------------------");
      console.log(`Name: ${overview.name}`);
      console.log(`Country: ${overview.country}`);
      console.log(`Age: ${overview.age}`);
      console.log(`Height: ${overview.height}`);
      console.log(`Weight: ${overview.weight}`);
      console.log(`Current Rank: ${overview.rank}`);
      console.log(`Career High Rank: ${overview.careerHighRank}`);
      console.log(`Career Win/Loss: ${overview.winLoss}`);
      console.log(`Season Win/Loss: ${performance.seasonWL}`);
      console.log(`Titles: ${overview.titles}`);
      console.log(`Grand Slams: ${slams}`);

      console.log("\n📊 Surface Records");
      for (const [surface, record] of Object.entries(performance.surfaces)) {
        console.log(`${surface}: ${record}`);
      }

      console.log("\n🕒 Recent Matches");
      matches.forEach((m, i) => {
        console.log(
          `${i + 1}. ${m.tournament} | ${m.round} | vs ${m.opponent} | ${m.result}`
        );
      });

      console.log("--------------------------------------------------");
      rl.close();
    });
  });
}

main();