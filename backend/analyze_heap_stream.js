const fs = require('fs');
const readline = require('readline');

// CONFIG
const SNAPSHOT_FILE = process.argv[2] || 'Heap.heapsnapshot';
const TARGET_STRINGS = ['Mesh', 'Vector3', 'Matrix4', 'Object3D', 'BufferGeometry'];

async function analyze() {
    console.log(`Analyzing ${SNAPSHOT_FILE} using Streams...`);

    // 1. First Pass: Read "strings" array to map Index -> String
    // Unfortuantely "strings" array is usually at the END of the file.
    // And "nodes" uses indices. 
    // If we can't load the file, we can't easily map.

    // ALTERNATIVE STRATEGY:
    // Just count the occurrences of specific string patterns in the raw file stream.
    // In a heap snapshot, strings are stored as JSON strings: "Mesh", "Vector3".
    // Occurrences in the "nodes" array are INTEGERS (indices).
    // So looking for "Mesh" in the file will only tell us if the string DEFINITION exists (it usually does once).
    // It won't tell us how many objects there are.

    // HOWEVER: The "nodes" array contains integers.
    // If we want to know if we have 10 million objects, we need to count the nodes.
    // Structure: "nodes":[type, name_idx, id, self_size, edge_count, trace_node_id, ...]

    // If we can count the commas in the "nodes" array, divided by stride (usually 6 or 7), we get object count.

    const stream = fs.createReadStream(SNAPSHOT_FILE, { encoding: 'utf8', highWaterMark: 64 * 1024 });

    let inNodes = false;
    let bracketDepth = 0;
    let nodeCount = 0;

    // Very rough parser
    let buffer = '';

    stream.on('data', (chunk) => {
        // Simple search for "nodes":[
        if (!inNodes) {
            const idx = chunk.indexOf('"nodes":[');
            if (idx !== -1) {
                inNodes = true;
                // We are now in nodes array
                // We need to count items (approx by commas)
            }
        }

        if (inNodes) {
            // Count commas
            for (let i = 0; i < chunk.length; i++) {
                if (chunk[i] === ',') nodeCount++;
                if (chunk[i] === ']') {
                    // End of nodes?
                    // This is risky if strings contain ']', but nodes array is usually integers.
                    // Let's assume valid snapshot structure.
                    console.log("End of nodes array detected (rough).");
                    inNodes = false;
                    stream.destroy(); // Stop reading
                }
            }
        }
    });

    stream.on('close', () => {
        // Default Stride is 7 usually.
        // Chrome DevTools: [type, name, id, self_size, edge_count, trace_node_id, detachedness] = 7 fields?
        // Let's assume 6 or 7.
        const estimatedNodes = nodeCount / 7;
        console.log(`Total Commas in 'nodes': ${nodeCount}`);
        console.log(`Estimated Objects (Stride 7): ${Math.floor(nodeCount / 7).toLocaleString()}`);
        console.log(`Estimated Objects (Stride 6): ${Math.floor(nodeCount / 6).toLocaleString()}`);

        // If we see 10 million objects, that's heavy.
    });
}

// Second Script for Grepping
// We can use unix `grep -c` for "detached" or specific attributes? 
// No, the snapshot is integers.
// But we can check for "Snapshot size" logic.

analyze();
