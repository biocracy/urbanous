
const fs = require('fs');
const filePath = process.argv[2];

if (!filePath) {
    console.error("Usage: node check_syntax.js <filepath>");
    process.exit(1);
}

const content = fs.readFileSync(filePath, 'utf8');
const lines = content.split('\n');

let balance = {
    '{': 0,
    '(': 0,
    '[': 0,
    '<div': 0, // Rudimentary tag check
};

let stack = [];

for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    // Ignore comments (basic)
    const stripped = line.replace(/\/\/.*/, '').replace(/\/\*.*?\*\//g, '');

    for (let char of stripped) {
        if (char === '{') { balance['{']++; stack.push({ char, line: i + 1 }); }
        if (char === '(') { balance['(']++; stack.push({ char, line: i + 1 }); }
        if (char === '[') { balance['[']++; stack.push({ char, line: i + 1 }); }

        if (char === '}') {
            balance['{']--;
            const last = stack.pop();
            if (last && last.char !== '{') console.log(`Mismatch at line ${i + 1}: Found } but expected closing for ${last.char} from line ${last.line}`);
        }
        if (char === ')') {
            balance['(']--;
            const last = stack.pop();
            if (last && last.char !== '(') console.log(`Mismatch at line ${i + 1}: Found ) but expected closing for ${last.char} from line ${last.line}`);
        }
        if (char === ']') {
            balance['[']--;
            const last = stack.pop();
            if (last && last.char !== '[') console.log(`Mismatch at line ${i + 1}: Found ] but expected closing for ${last.char} from line ${last.line}`);
        }
    }
}

console.log("Final Balance:", balance);
if (stack.length > 0) {
    console.log("Unclosed items:");
    stack.slice(-5).forEach(item => console.log(`${item.char} at line ${item.line}`));
}
