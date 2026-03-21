const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Load topics
const topicsPath = path.join(__dirname, 'topics.json');
const topics = JSON.parse(fs.readFileSync(topicsPath, 'utf-8'));
const topicKeys = Object.keys(topics);

// Precompile regex patterns for valid folders
const validPatterns = {};
for (const key of topicKeys) {
  // Match: {timestamp}_{sanitized_key}(_tmp)?
  const escapedKey = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/[/\\]|:|\*|\?|"|<|>|\|/g, '_');
  validPatterns[key] = new RegExp(`^\\d+_${escapedKey}(_tmp)?$`);
}

// Check if a folder represents a completed download for the given topic
function isAlreadyDownloaded(imagesFolder, topicKey) {
  if (!fs.existsSync(imagesFolder)) {
    return false;
  }

  const entries = fs.readdirSync(imagesFolder, { withFileTypes: true });

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;

    const name = entry.name;
    const dirPath = path.join(imagesFolder, name);
    // Pattern: {timestamp}_{topic}
    if (validPatterns[topicKey].test(name) && !/\_tmp$/.test(dirPath)) {
      const hasImagesInfo = fs.existsSync(path.join(dirPath, 'images_info.json'));
      const hasImages = fs.readdirSync(dirPath).some(file =>
        ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'].includes(path.extname(file).toLowerCase())
      );
      if (hasImagesInfo && hasImages) {
        return true;
      }
    }
  }

  return false;
}

// Cleanup invalid folders (folders that don't match any topic pattern)
function cleanupInvalidFolders(imagesFolder) {
  if (!fs.existsSync(imagesFolder)) {
    console.log('Images folder not found, skipping cleanup');
    return { deleted: 0, kept: 0 };
  }

  let deleted = 0;
  let kept = 0;
  const entries = fs.readdirSync(imagesFolder, { withFileTypes: true });

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;

    const name = entry.name;

    // Skip if doesn't look like a timestamped folder
    if (!/^\d+/.test(name)) continue;

    // Check if it matches any valid topic pattern
    let isValid = false;
    for (const key of topicKeys) {
      if (validPatterns[key].test(name)) {
        const dirPath = path.join(imagesFolder, name);
        const hasImagesInfo = fs.existsSync(path.join(dirPath, 'images_info.json'));
        const hasImages = fs.readdirSync(dirPath).some(file =>
          ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'].includes(path.extname(file).toLowerCase())
        );
        if (hasImagesInfo && hasImages) {
          isValid = true;
          break;
        }
      }
    }

    if (isValid) {
      kept++;
    } else {
      // Delete invalid folder
      try {
        const dirPath = path.join(imagesFolder, name);
        fs.rmSync(dirPath, { recursive: true });
        console.log(`  Deleted invalid folder: ${name}`);
        deleted++;
      } catch (e) {
        console.log(`  Failed to delete ${name}: ${e.message}`);
      }
    }
  }

  console.log(`Cleanup: ${deleted} invalid folders deleted, ${kept} valid folders kept`);
  console.log('='.repeat(60));
  return { deleted, kept };
}

// Cleanup _tmp folders for a specific topic (from previous failed runs)
function cleanupTopicTmpFolder(imagesFolder, topicKey) {
  if (!fs.existsSync(imagesFolder)) {
    return 0;
  }

  let deleted = 0;
  const entries = fs.readdirSync(imagesFolder, { withFileTypes: true });

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;

    const name = entry.name;

    // Check if this is a _tmp folder for the given topic
    if (validPatterns[topicKey].test(name) && name.endsWith('_tmp')) {
      // Delete all _tmp folders for this topic (they represent incomplete/unfinalized downloads)
      const dirPath = path.join(imagesFolder, name);
      try {
        fs.rmSync(dirPath, { recursive: true });
        console.log(`  🗑️  Deleted previous _tmp folder: ${name}`);
        deleted++;
      } catch (e) {
        console.log(`  Failed to delete ${name}: ${e.message}`);
      }
    }
  }

  return deleted;
}

// Download a single topic
async function downloadTopic(topicKey, topicChinese, baseDir, imagesFolder) {
  return new Promise((resolve) => {
    const cmd = process.platform === 'win32' ? 'python' : 'python3';
    const doodlesScript = path.join(baseDir, 'doodles.py');
    const args = [doodlesScript, '--query', `topic_tags=${topicKey}`];

    const proc = spawn(cmd, args, {
      cwd: baseDir,
      stdio: ['ignore', 'inherit', 'inherit']
    });

    proc.on('close', (code) => {
      if (code === 0) {
        resolve({ topicKey, success: true });
      } else {
        resolve({ topicKey, success: false });
      }
    });
  });
}

// Main function
async function main() {
  const args = process.argv.slice(2);
  const options = {
    type: 'topic',
    workers: 3
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--type' && args[i + 1]) {
      options.type = args[++i];
    } else if (args[i] === '--workers' && args[i + 1]) {
      options.workers = parseInt(args[++i], 10);
    }
  }

  if (options.type !== 'topic') {
    console.error(`Error: Unsupported type '${options.type}'. Currently only 'topic' is supported.`);
    process.exit(1);
  }

  console.log(`Found ${topicKeys.length} topics to process`);
  console.log(`Using ${options.workers} parallel workers`);
  console.log('Press Ctrl+C at any time to gracefully stop (once)');
  console.log('='.repeat(60));

  const baseDir = __dirname;
  const imagesFolder = path.join(baseDir, 'images');

  // Cleanup before starting
  cleanupInvalidFolders(imagesFolder);

  let skipped = 0;
  let completed = 0;
  let failed = 0;

  // Process topics with parallel workers
  const workerPromises = [];
  const activeWorkers = new Set();

  for (const topicKey of topicKeys) {
    // Wait if at max workers
    while (activeWorkers.size >= options.workers) {
      await new Promise(resolve => {
        for (const p of activeWorkers) {
          p.finally(() => {
            activeWorkers.delete(p);
            resolve();
          });
        }
      });
    }

    const topicChinese = topics[topicKey];
    console.log(`  ▶️  start downloading: ${topicKey} (${topicChinese})`);

    // Check if already downloaded
    if (isAlreadyDownloaded(imagesFolder, topicKey)) {
      console.log(`  ⏭️  Skipping ${topicKey}: Already downloaded`);
      skipped++;
      continue;
    }

    // Cleanup any previous failed _tmp folder for this topic before starting
    const cleanupCount = cleanupTopicTmpFolder(imagesFolder, topicKey);
    if (cleanupCount > 0) {
      console.log(`  🗑️  Cleaned up ${cleanupCount} previous failed _tmp folder(s)`);
    }

    const promise = downloadTopic(topicKey, topicChinese, baseDir, imagesFolder)
      .then(result => {
        if (result.success) {
          completed++;
        } else if (isAlreadyDownloaded(imagesFolder, topicKey)) {
          skipped++;
        } else {
          failed++;
        }
      })
      .catch(err => {
        console.log(`  ❌ Error for ${topicKey}: ${err.message || err}`);
        failed++;
      })
      .finally(() => {
        activeWorkers.delete(promise);
      });

    activeWorkers.add(promise);
    workerPromises.push(promise);
  }

  // Wait for all to complete
  await Promise.all(workerPromises);

  // Summary
  console.log('\n' + '='.repeat(60));
  console.log('Batch processing complete!');
  console.log(`  Total topics: ${topicKeys.length}`);
  console.log(`  Skipped (already downloaded): ${skipped}`);
  console.log(`  Completed this run: ${completed}`);
  console.log(`  Failed: ${failed}`);
  console.log('='.repeat(60));
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n\n⚠️  Received interrupt signal, shutting down...');
  process.exit(0);
});
process.on('SIGTERM', () => {
  console.log('\n\n⚠️  Received terminate signal, shutting down...');
  process.exit(0);
});

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});