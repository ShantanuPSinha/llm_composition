const fs = require('fs');
const readline = require('readline');
const path = require('path');

function parseNDJSONLine(line) {
    try {
        return JSON.parse(line);
    } catch (error) {
        console.error('Error parsing NDJSON line:', error);
        return null;
    }
}

async function readNDJSONFile(filePath) {
    const fileStream = fs.createReadStream(filePath);
    const rl = readline.createInterface({
        input: fileStream,
        crlfDelay: Infinity
    });

    const data = [];
    for await (const line of rl) {
        const obj = parseNDJSONLine(line);
        if (obj) {
            data.push(obj);
        }
    }
    return data;
}

function parseTextFile(filePath) {
    const content = fs.readFileSync(filePath, 'utf-8');
    const parts = content.split('---');
    const positivePart = parts[0].includes('+++') ? parts[0].split('+++')[1] : '';
    const negativePart = parts.length > 1 ? parts[1] : '';
    const positiveExamples = positivePart.trim().split('\n');
    const negativeExamples = negativePart.trim().split('\n');
    return { positiveExamples, negativeExamples };
}

// Function to test GPT response regex
function testGPTResponseRegex(regex, positiveExamples, negativeExamples) {
    try {
        const regexObj = new RegExp(regex);
        const pass = positiveExamples.every(example => regexObj.test(example)) &&
                     negativeExamples.every(example => !regexObj.test(example));
        return { isValid: true, pass };
    } catch (error) {
        return { isValid: false, pass: false };
    }
}

// Function to process NDJSON objects with regex validation and testing
async function processNDJSONObject(ndjsonObj, directoryPath) {
    const { file_id, 'GPT-response': gptResponse } = ndjsonObj;
    const txtFiles = fs.readdirSync(directoryPath).filter(file => file.endsWith('.txt'));
    const matchingFile = txtFiles.find(file => parseInt(path.parse(file).name) === file_id);
    if (matchingFile) {
        const filePath = path.join(directoryPath, matchingFile);
        const { positiveExamples, negativeExamples } = parseTextFile(filePath);
        const { isValid, pass } = testGPTResponseRegex(gptResponse, positiveExamples, negativeExamples);
        
        ndjsonObj.Valid_Regex = isValid;
        ndjsonObj.pass = pass;
    } else {
        ndjsonObj.pass = 'File not found';
    }
    return ndjsonObj;
}

// Function to process NDJSON file
async function processNDJSONFile(ndjsonFilePath, directoryPath) {
    try {
        const ndjsonData = await readNDJSONFile(ndjsonFilePath);
        const processedData = await Promise.all(ndjsonData.map(obj => processNDJSONObject(obj, directoryPath)));
        const ndjsonString = processedData.map(obj => JSON.stringify(obj)).join('\n');
        fs.writeFileSync(ndjsonFilePath, ndjsonString);
    } catch (error) {
        console.error('Error processing NDJSON file:', error);
    }
}

function printStatistics(filePath) {
    const data = fs.readFileSync(filePath, 'utf-8').split('\n').map(JSON.parse);
    const totalDicts = data.length;
    const validCount = data.filter(d => d.Valid_Regex).length;
    const passedCount = data.filter(d => d.pass).length;
    const validPercentage = (validCount / totalDicts) * 100;
    const passedPercentage = (passedCount / totalDicts) * 100;
    
    console.log(`Total: ${totalDicts}\nValid: ${validCount}, Passed: ${passedCount}`);
    console.log(`Valid percentage: ${validPercentage.toFixed(2)}%, Passed percentage: ${passedPercentage.toFixed(2)}%`);
}

const ndjsonFilePath = '/home/shantanu/duality/llm_composition/gpt_output.ndjson';
const directoryPath = '/home/shantanu/duality/Xtractor/temp/rfixer_output';
processNDJSONFile(ndjsonFilePath, directoryPath);
printStatistics(ndjsonFilePath);
