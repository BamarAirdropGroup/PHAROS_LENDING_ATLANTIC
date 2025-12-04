import { ethers } from "ethers";
import fs from "fs";
import path from "path";

const rpc = "https://api.zan.top/node/v1/pharos/atlantic/be53891571bc44dc9e1acffd0155bbd7";
const provider = new ethers.JsonRpcProvider(rpc);

const lendingContractAddress = "0x62e72185f7deabda9f6a3df3b23d67530b42eff6";
const WBTC_CA = "0x0c64f03eea5c30946d5c55b4b532d08ad74638a4";

const ABI = [
  "function approve(address spender, uint256 amount) external returns (bool)",
];

const accountsFilePath = path.resolve("accounts.txt");
let privateKeys = [];

try {
  const data = fs.readFileSync(accountsFilePath, "utf-8");
  privateKeys = data
    .split("\n")
    .map(line => line.trim())
    .filter(line => line.length === 64 || (line.startsWith("0x") && line.length === 66))
    .map(key => key.startsWith("0x") ? key : "0x" + key);

  console.log(`Loaded ${privateKeys.length} private keys from accounts.txt\n`);
} catch (err) {
  console.error("Cannot read accounts.txt – make sure the file exists in the same folder!");
  process.exit(1);
}

if (privateKeys.length === 0) {
  console.error("No valid private keys found!");
  process.exit(1);
}


const DELAY_BETWEEN_WALLETS = 3000; 
const DELAY_BETWEEN_TXS = 1500; 
const MAX_RETRIES = 15;
const RETRY_MIN_DELAY = 2000; 
const RETRY_MAX_DELAY = 8000; 


async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function randomDelay(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

async function withRetry(fn, operationName, walletAddress) {
  let lastError;
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;
      const shortMsg = err.message?.split("\n")[0] || err.toString();
      console.log(` ${operationName} failed (attempt ${attempt}/${MAX_RETRIES}): ${shortMsg}`);

      if (attempt < MAX_RETRIES) {
        const delay = randomDelay(RETRY_MIN_DELAY, RETRY_MAX_DELAY);
        console.log(` Retrying in ${delay/1000}s...`);
        await sleep(delay);
      }
    }
  }
  console.log(` ${operationName} permanently failed after ${MAX_RETRIES} attempts`);
  throw lastError; 
}

for (let i = 0; i < privateKeys.length; i++) {
  const pk = privateKeys[i];
  const wallet = new ethers.Wallet(pk, provider);
  const address = wallet.address;
  console.log(`\nWallet ${i + 1}/${privateKeys.length}: ${address}`);

  try {
    
    console.log(" Approving WBTC...");
    const tokenContract = new ethers.Contract(WBTC_CA, ABI, wallet);

    await withRetry(async () => {
      const amount = ethers.parseUnits("1000", 8);
      const tx = await tokenContract.approve(lendingContractAddress, amount);
      console.log(` Approve tx sent: ${tx.hash}`);
      await tx.wait(1);
      console.log(" Approve confirmed");
    }, "Approve", address);

    
    const AddressLowerNo0x = address.slice(2).toLowerCase();
    const calldata = `0x617ba0370000000000000000000000000c64f03eea5c30946d5c55b4b532d08ad74638a400000000000000000000000000000000000000000000000000000002540be400000000000000000000000000${AddressLowerNo0x}0000000000000000000000000000000000000000000000000000000000000000`;

    for (let j = 0; j < 45; j++) {
      await withRetry(async () => {
        
        const tx = {
          to: lendingContractAddress,
          data: calldata,
          gasLimit: 500000, 
          gasPrice: await provider.getFeeData().gasPrice || undefined,
        };

        const sentTx = await wallet.sendTransaction(tx);
        console.log(` Lending tx ${j + 1}/45 sent: https://atlantic.pharosscan.xyz/tx/${sentTx.hash}`);

        
      }, `Lending tx ${j + 1}/45`, address);

      if (j < 44) await sleep(DELAY_BETWEEN_TXS);
    }

    console.log(`Wallet ${address} COMPLETED SUCCESSFULLY!`);

  } catch (err) {
    console.error(`Wallet ${address} FAILED AFTER ALL RETRIES:`, err.message || err);
  }

  
  if (i < privateKeys.length - 1) {
    console.log(`Waiting ${DELAY_BETWEEN_WALLETS / 1000}s before next wallet...\n`);
    await sleep(DELAY_BETWEEN_WALLETS);
  }
}

console.log("\nALL WALLETS PROCESSED!");
