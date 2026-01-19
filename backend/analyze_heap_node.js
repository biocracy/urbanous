const fs = require('fs');
const readline = require('readline');

const SNAPSHOT_FILE = process.argv[2] || 'Heap.heapsnapshot';

async function analyze() {
    console.log(`Analyzing ${SNAPSHOT_FILE}...`);

    // We need to read specific sections: "snapshot", "nodes", "strings"
    // Since it's a massive single-line JSON usually, we can't just line-read.
    // BUT Chrome snapshots are structure: { snapshot: {...}, nodes: [...], strings: [...] }
    // We can try to use a streaming JSON parser or a manual buffer scan.

    // For simplicity given the environment: 
    // Let's assume we can read the "snapshot" meta part easily (it's at the start).
    // Then counting commas for nodes.

    // Actually, let's use a simpler heuristic for a 3GB file without 'stream-json' dependency:
    // We will look for repeating string patterns in the raw file if possible? No, that's binary-ish.

    // Better approach: Python with 'ijson' or just standard 'json' allows chunk reading? No.
    // Let's force Python to read it line by line? Chrome snapshots are often ONE line.

    // Plan B: Grep gave us "1" for Mesh. This implies the strings are in the "strings" array at the end.
    // If we count "Mesh" in the file, we find the string definition.
    // But we need to know how many NODES use that string.

    // Let's try Node.js with a large max-old-space-size first.
    // 3GB file might fit in 8GB RAM if we are careful.

    try {
        const data = fs.readFileSync(SNAPSHOT_FILE, 'utf8');
        console.log("File loaded into RAM. Parsing JSON...");
        const json = JSON.parse(data);
        console.log("JSON Parsed.");

        const nodes = json.nodes;
        const strings = json.strings;
        const classes = {};

        // Meta
        const meta = json.snapshot.meta;
        const node_fields = meta.node_fields;
        const node_types = meta.node_types[0]; // usually 0 is type
        const type_offset = node_fields.indexOf('type');
        const name_offset = node_fields.indexOf('name');
        const stride = node_fields.length;

        console.log(`Nodes: ${nodes.length / stride}`);

        const counts = {};

        for (let i = 0; i < nodes.length; i += stride) {
            const typeIdx = nodes[i + type_offset];
            const type = node_types[typeIdx];

            const nameIdx = nodes[i + name_offset];
            const name = strings[nameIdx];

            if (!counts[name]) counts[name] = 0;
            counts[name]++;

            if (!classes[type]) classes[type] = 0;
            classes[type]++;
        }

        console.log("--- Types ---");
        console.log(classes);

        console.log("--- Top 50 Names ---");
        Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 50)
            .forEach(([k, v]) => console.log(`${k}: ${v}`));

    } catch (e) {
        console.error("Error:", e.message);
        console.log("Attempting stream scan for 'Mesh'...");
        // Fallback or suggestion
    }
}

analyze();
