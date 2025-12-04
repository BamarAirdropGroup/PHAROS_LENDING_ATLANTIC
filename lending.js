import { ethers } from "ethers";
import dotenv from "dotenv";

dotenv.config();
const rpc =
  "https://api.zan.top/node/v1/pharos/atlantic/be53891571bc44dc9e1acffd0155bbd7";
const provider = new ethers.JsonRpcProvider(rpc);

const lendingContractAddress = "0x62e72185f7deabda9f6a3df3b23d67530b42eff6";
const WBTC_CA = "0x0c64f03eea5c30946d5c55b4b532d08ad74638a4";
const ABI = [
  "function approve(address spender, uint256 amount) external returns (bool)",
];
const privateKeys = Array.from(
  { length: 100 },
  (_, i=1) => process.env[`PRIVATE_KEY_${i + 1}`]
).filter(Boolean);
for (const keys of privateKeys) {
  const wallet = new ethers.Wallet(keys, provider);
  const Address = wallet.address.slice(2).toLowerCase();
  const tokenContract = new ethers.Contract(WBTC_CA, ABI, wallet);
  await tokenContract.approve(
    lendingContractAddress,
    ethers.parseUnits("1000", 8)
  );
  console.log(`Approved WBTC for wallet: ${wallet.address}`);
  for (let i = 0; i < 45; i++) {
    const calldata = `0x617ba0370000000000000000000000000c64f03eea5c30946d5c55b4b532d08ad74638a400000000000000000000000000000000000000000000000000000002540be400000000000000000000000000${Address}0000000000000000000000000000000000000000000000000000000000000000`;

    const tx = {
      to: lendingContractAddress,
      data: calldata,
    };
    await wallet.sendTransaction(tx);
    console.log("lending Transaction sent");
  }
}
