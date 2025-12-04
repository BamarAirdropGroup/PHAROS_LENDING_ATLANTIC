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

  console.log(`Loaded ${privateKeys.length} private keys from accounts.txt`);
} catch (err) {
  console.error("Cannot read accounts.txt – make sure the file exists in the same folder!");
  process.exit(1);
}

if (privateKeys.length === 0) {
  console.error("No valid private keys found!");
  process.exit(1);
}


const DELAY_BETWEEN_WALLETS = 3000; 
const DELAY_BETWEEN_TXS     = 1500; 

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

for (let i = 0; i < privateKeys.length; i++) {
  const pk = privateKeys[i];
  const wallet = new ethers.Wallet(pk, provider);
  const address = wallet.address;
  console.log(`\nProcessing wallet ${i + 1}/${privateKeys.length}: ${address}`);

  try {
    
    const tokenContract = new ethers.Contract(WBTC_CA, ABI, wallet);
    const approveTx = await tokenContract.approve(
      lendingContractAddress,
      ethers.parseUnits("1000", 8) 
    );
    console.log(`Approve tx sent: ${approveTx.hash}`);
    await approveTx.wait();
    console.log("Approve confirmed");

    
    const AddressLowerNo0x = address.slice(2).toLowerCase();
    const calldata = `0x617ba0370000000000000000000000000c64f03eea5c30946d5c55b4b532d08ad74638a400000000000000000000000000000000000000000000000000000002540be400000000000000000000000000${AddressLowerNo0x}0000000000000000000000000000000000000000000000000000000000000000`;

    for (let j = 0; j < 45; j++) {
      const tx = {
        to: lendingContractAddress,
        data: calldata,
        
      };

      const sentTx = await wallet.sendTransaction(tx);
      console.log(`Lending tx ${j + 1}/45 sent: https://atlantic.pharosscan.xyz/tx/${sentTx.hash}`);

      
      await sleep(DELAY_BETWEEN_TXS);
    }

    console.log(`Wallet ${address} completed!`);
  } catch (err) {
    console.error(`Error with wallet ${address}:`, err.message || err);
  }

 
  if (i < privateKeys.length - 1) {
    console.log(`Waiting ${DELAY_BETWEEN_WALLETS / 1000}s before next wallet...`);
    await sleep(DELAY_BETWEEN_WALLETS);
  }
}

console.log("\nAll wallets processed!");
