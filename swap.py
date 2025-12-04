from web3 import Web3
from eth_account import Account
from aiohttp import ClientSession, ClientTimeout, BasicAuth
from aiohttp_socks import ProxyConnector
from datetime import datetime
from colorama import init, Fore, Style
import asyncio, random, time, os, pytz, re, sys

init(autoreset=True)
wib = pytz.timezone('Asia/Jakarta')

class Faroswap:
    def __init__(self):
        self.RPC_URL = "https://api.zan.top/node/v1/pharos/atlantic/be53891571bc44dc9e1acffd0155bbd7"
        self.EXPLORER = "https://atlantic.pharosscan.xyz/tx/0x"
        
        self.PHRS = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"   
        self.WBTC = "0x0c64f03eea5c30946d5c55b4b532d08ad74638a4"  

        self.DODO_APPROVE = "0x4Cf317b8918FbE8A890c01eDAb7d548555Ac2cE9"
        self.DODO_ROUTER = "0x819829e5CF6e19F9fED92F6b4CC1edF45a2cC4A2"

        self.ABI = [
            {"inputs": [{"internalType": "address", "name": "owner", "type": "address"}, {"internalType": "address", "name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"internalType": "address", "name": "spender", "type": "address"}, {"internalType": "uint256", "name": "value", "type": "uint256"}], "name": "approve", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"internalType": "address", "name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "decimals", "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"}
        ]

        self.proxies = []
        self.account_proxies = {}
        self.proxy_index = 0
        self.use_proxy = False

        # User config
        self.swap_count = 1
        self.phrs_amount = 0.001
        self.min_delay = 5
        self.max_delay = 15

    def log(self, msg):
        print(f"{Fore.CYAN}[ {datetime.now().astimezone(wib).strftime('%m/%d/%y %H:%M:%S')} ]{Fore.WHITE} | {msg}{Style.RESET_ALL}", flush=True)

    async def load_proxies(self, choice):
        filename = "proxy.txt"
        try:
            if choice == 1:
                async with ClientSession(timeout=ClientTimeout(total=30)) as session:
                    async with session.get("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt") as resp:
                        text = await resp.text()
                        with open(filename, "w") as f:
                            f.write(text)
                        self.proxies = [l.strip() for l in text.splitlines() if l.strip()]
            else:
                if not os.path.exists(filename):
                    self.log(f"{Fore.RED}proxy.txt not found!{Style.RESET_ALL}")
                    return
                with open(filename) as f:
                    self.proxies = [l.strip() for l in f.read().splitlines() if l.strip()]

            if self.proxies:
                self.log(f"{Fore.GREEN}Loaded {len(self.proxies)} proxies{Style.RESET_ALL}")
                self.use_proxy = True
        except Exception as e:
            self.log(f"{Fore.RED}Proxy error: {e}{Style.RESET_ALL}")

    def get_proxy(self, addr):
        if not self.use_proxy or not self.proxies:
            return None
        if addr not in self.account_proxies:
            proxy = self.proxies[self.proxy_index % len(self.proxies)]
            if not proxy.startswith(("http", "socks")):
                proxy = "http://" + proxy
            self.account_proxies[addr] = proxy
            self.proxy_index += 1
        return self.account_proxies[addr]

    async def get_web3(self):
        for _ in range(5):
            try:
                w3 = Web3(Web3.HTTPProvider(self.RPC_URL, request_kwargs={"timeout": 60}))
                if await asyncio.to_thread(w3.is_connected):
                    return w3
            except:
                await asyncio.sleep(2)
        raise Exception("RPC Failed")

    async def fresh_nonce(self, w3, addr):
        return await asyncio.to_thread(w3.eth.get_transaction_count, addr, "pending")

    async def swap(self, pk, addr):
        w3 = await self.get_web3()
        amount_wei = w3.to_wei(self.phrs_amount, 'ether')

        # Get route
        route = None
        for attempt in range(15):
            proxy = self.get_proxy(addr)
            try:
                async with ClientSession(timeout=ClientTimeout(total=60)) as s:
                    if proxy and proxy.startswith("socks"):
                        connector = ProxyConnector.from_url(proxy)
                        s = ClientSession(timeout=ClientTimeout(total=60), connector=connector)
                    async with s.get(
                        "https://api.dodoex.io/route-service/v2/widget/getdodoroute",
                        params={
                            "chainId": "688689",
                            "fromTokenAddress": self.PHRS,
                            "toTokenAddress": self.WBTC,
                            "fromAmount": str(amount_wei),
                            "userAddr": addr,
                            "slippage": "5",
                            "deadLine": int(time.time()) + 600,
                            "source": "dodoV2AndMixWasm",
                            "estimateGas": "true",
                            "apikey": "a37546505892e1a952"
                        },
                        proxy=proxy if proxy and proxy.startswith("http") else None
                    ) as r:
                        data = await r.json()

                if data.get("status") == 200:
                    route = data["data"]
                    break
                else:
                    self.log(f"{Fore.YELLOW}No route, retry {attempt+1}/15...{Style.RESET_ALL}")
                    if self.use_proxy:
                        self.account_proxies.pop(addr, None)
                    await asyncio.sleep(3)
            except:
                if self.use_proxy:
                    self.account_proxies.pop(addr, None)
                await asyncio.sleep(3)

        if not route:
            self.log(f"{Fore.RED}Failed to get route after 15 tries{Style.RESET_ALL}")
            return False

        
        tx = {
            'to': Web3.to_checksum_address(self.DODO_ROUTER),
            'data': route["data"],
            'value': int(route["value"]),
            'gas': int(route["gasLimit"]) + 200000,
            'maxFeePerGas': w3.to_wei(random.uniform(3.0, 4.5), 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(random.uniform(1.5, 2.8), 'gwei'),
            'nonce': await self.fresh_nonce(w3, addr),
            'chainId': w3.eth.chain_id
        }

        for _ in range(5):
            try:
                signed = w3.eth.account.sign_transaction(tx, pk)
                hash_tx = w3.eth.send_raw_transaction(signed.raw_transaction)
                self.log(f"{Fore.YELLOW}TX Sent → {hash_tx.hex()}{Style.RESET_ALL}")

                receipt = await asyncio.to_thread(w3.eth.wait_for_transaction_receipt, hash_tx, timeout=300)
                if receipt.status == 1:
                    self.log(f"{Fore.GREEN}SWAP SUCCESS! {self.phrs_amount} PHRS → WBTC{Style.RESET_ALL}")
                    self.log(f"{Fore.CYAN}Explorer → {self.EXPLORER}{hash_tx.hex()}{Style.RESET_ALL}\n")
                    return True
                else:
                    self.log(f"{Fore.RED}TX Reverted{Style.RESET_ALL}\n")
                    return False
            except Exception as e:
                if "nonce" in str(e).lower() or "replay" in str(e).lower():
                    tx['nonce'] = await self.fresh_nonce(w3, addr)
                elif "insufficient" in str(e).lower():
                    self.log(f"{Fore.RED}Insufficient balance/gas{Style.RESET_ALL}")
                    return False
                await asyncio.sleep(3)
        return False

    async def delay(self):
        delay = random.randint(self.min_delay, self.max_delay)
        for i in range(delay, 0, -1):
            print(f"{Fore.BLUE}Next wallet in {i}s...{Style.RESET_ALL}", end="\r", flush=True)
            await asyncio.sleep(1)
        print(" " * 60, end="\r", flush=True)

    async def menu(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Fore.GREEN + Style.BRIGHT}   PHAROS ATLANTIC → WBTC ONE-TIME SWAP BOT{Style.RESET_ALL}\n")

        print(f"{Fore.YELLOW}Proxy Settings:{Style.RESET_ALL}")
        print(f"  0 → No Proxy (Fastest)")
        print(f"  1 → Download Fresh Proxies")
        print(f"  2 → Use proxy.txt")
        choice = input(f"{Fore.CYAN}Choose → {Style.RESET_ALL}") or "0"
        if choice in ["1", "2"]:
            await self.load_proxies(int(choice))
        else:
            self.log(f"{Fore.YELLOW}Using Direct Connection (No Proxy){Style.RESET_ALL}")

        self.swap_count = int(input(f"\n{Fore.YELLOW}Swap Count per Wallet → {Style.RESET_ALL}") or "1")
        self.phrs_amount = float(input(f"{Fore.YELLOW}PHRS Amount per Swap  → {Style.RESET_ALL}") or "0.001")
        self.min_delay = int(input(f"{Fore.YELLOW}Min Delay (seconds)   → {Style.RESET_ALL}") or "5")
        self.max_delay = int(input(f"{Fore.YELLOW}Max Delay (seconds)   → {Style.RESET_ALL}") or "15")

        print(f"\n{Fore.GREEN + Style.BRIGHT}Bot Starting... All wallets will run once then EXIT{Style.RESET_ALL}\n")

    async def run(self):
        await self.menu()

        if not os.path.exists("accounts.txt"):
            self.log(f"{Fore.RED + Style.BRIGHT}accounts.txt NOT FOUND!{Style.RESET_ALL}")
            return

        with open("accounts.txt") as f:
            keys = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        if not keys:
            self.log(f"{Fore.RED}No private keys found in accounts.txt{Style.RESET_ALL}")
            return

        self.log(f"{Fore.GREEN + Style.BRIGHT}Starting {len(keys)} wallets → PHRS → WBTC Swap (One-time only){Style.RESET_ALL}\n")

        for idx, pk in enumerate(keys, 1):
            try:
                addr = Account.from_key(pk).address
                self.log(f"{Fore.MAGENTA}═'═'*25 WALLET {idx}/{len(keys)} '═'*25{Style.RESET_ALL}")
                self.log(f"{Fore.WHITE}Address → {addr}{Style.RESET_ALL}")

                for i in range(self.swap_count):
                    self.log(f"{Fore.CYAN}Swap {i+1}/{self.swap_count} → {self.phrs_amount} PHRS → WBTC")
                    await self.swap(pk, addr)
                    if i < self.swap_count - 1:
                        await self.delay()

                if idx < len(keys):
                    await self.delay()

            except Exception as e:
                self.log(f"{Fore.RED}Wallet {idx} failed: {e}{Style.RESET_ALL}")

        # Final message and EXIT
        print(f"\n{Fore.GREEN + Style.BRIGHT}ALL WALLETS PROCESSED SUCCESSFULLY!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Bot finished. Exiting in 5 seconds...{Style.RESET_ALL}")
        await asyncio.sleep(5)
        sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(Faroswap().run())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Stopped by user.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
