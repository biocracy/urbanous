
const fs = require('fs');

const rawText = fs.readFileSync('temp_digest_13.md', 'utf8');

console.log("--- RAW TEXT START ---");
console.log(rawText.slice(0, 500));
console.log("--- RAW TEXT END ---\n");

// Replicate NewsCard Logic
const lines = rawText.split('\n');
let chosenParagraph = "";

for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith('!')) continue;
    if (trimmed.startsWith('#')) continue;
    if (trimmed.startsWith('---')) continue;
    if (trimmed.match(/^(Summary|Digest|Report|Brief):?/i)) continue;

    console.log(`Checking line: [${trimmed.slice(0, 50)}] (Length: ${trimmed.length})`);

    if (trimmed.length > 40) {
        chosenParagraph = trimmed;
        console.log("-> CHOSEN!");
        break;
    }
}

if (!chosenParagraph) {
    console.log("-> FALLBACK LOGIC TRIGGERED");
    chosenParagraph = rawText
        .replace(/!\[.*?\]\(.*?\)/g, '')
        .replace(/^#+\s.*$/gm, '')
        .replace(/\n/g, ' ')
        .trim();
}

let clean = chosenParagraph
    .replace(/\(citation:\d+\)/g, '')
    .replace(/\[(.*?)\]\(.*?\)/g, '$1')
    .replace(/[*_`]/g, '')
    .trim();

// Remove Title Mock
const title = "Budget Impasse Dominates French Politics as Paris Prepares for Contentious Municipal Races";
if (clean.startsWith(title)) {
    clean = clean.substring(title.length).trim();
}

console.log("\n--- FINAL CLEAN SUMMARY ---");
console.log(clean);
