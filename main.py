import time
import asyncio
from web3 import Web3
import logging
from concurrent.futures import ThreadPoolExecutor
import os
from colorama import Fore, Style, init

init(autoreset=True)

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
       
sepolia_rpc_url = 'https://ethereum-sepolia-rpc.publicnode.com' # use https://www.alchemy.com/ for RPC
w3 = Web3(Web3.HTTPProvider(sepolia_rpc_url))

if not w3.is_connected():
    raise Exception("Failed to connect to Sepolia network")

def process_transaction(private_key, max_priority_fee, base_fee_multiplier):
    try:
        logging.info(f"Processing transaction for key: {private_key}")

        account = w3.eth.account.from_key(private_key)
        sender_address = account.address
        logging.info(f"Sender address: {sender_address}")

        address_no_prefix = sender_address[2:]
        data_template = f'0xc63d75b6000000000000000000000000{address_no_prefix}00000000000000000000000000000000000000000000003635c9adc5dea00000'

        base_fee = w3.eth.fee_history(1, 'latest')['baseFeePerGas'][-1]
        max_priority_fee_wei = w3.to_wei(max_priority_fee, 'gwei')
        gas_price = int(base_fee * base_fee_multiplier + max_priority_fee_wei)

        nonce = w3.eth.get_transaction_count(sender_address, 'pending')

        transaction = {
            'chainId': 11155111,
            'to': '0x800eC0D65adb70f0B69B7Db052C6bd89C2406aC4',
            'from': sender_address,
            'nonce': nonce,
            'maxFeePerGas': gas_price,
            'maxPriorityFeePerGas': max_priority_fee_wei,
            'gas': 0,
            'data': data_template,
            'value': 0
        }

        gas_limit = w3.eth.estimate_gas(transaction)
        logging.info(f"Estimated gas limit: {gas_limit}")
        transaction['gas'] = gas_limit

        signed_txn = w3.eth.account.sign_transaction(transaction, private_key)

        txn_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        print(Fore.GREEN + f"Transaction successful! Hash: {w3.to_hex(txn_hash)}")

    except Exception as e:
        print(Fore.RED + f"Error processing transaction with key {private_key}: {e}")

async def process_transactions_in_parallel(private_keys, num_transactions, max_priority_fee, base_fee_multiplier, sleep_time):
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as executor:
        for i in range(num_transactions):
            tasks = []
            for key in private_keys:
                key = key.strip()
                if key:
                    tasks.append(loop.run_in_executor(executor, process_transaction, key, max_priority_fee, base_fee_multiplier))
            await asyncio.gather(*tasks)
            await asyncio.sleep(sleep_time)

def manage_private_keys():
    private_keys = []
    if os.path.exists('private_keys.txt'):
        with open('private_keys.txt', 'r') as file:
            private_keys = file.readlines()

    if not private_keys:
        print(Fore.YELLOW + "No private keys found. Please enter a new private key:")
        new_key = input("Enter your private key: ")
        with open('private_keys.txt', 'w') as file:
            file.write(new_key + '\n')
        private_keys = [new_key]
    else:
        print(Fore.YELLOW + "Private keys found in 'private_keys.txt':")
        print(private_keys)
        answer = input("Do you want to continue with the current private key(s)? (yes/no): ").strip().lower()
        if answer == 'no':
            new_key = input("Enter your new private key: ")
            with open('private_keys.txt', 'w') as file:
                file.write(new_key + '\n')
            private_keys = [new_key]

    return private_keys

def get_input_with_default(prompt, default_value, value_type):
    user_input = input(f"{prompt} (default: {default_value}): ")
    if user_input.strip() == "":
        return default_value
    return value_type(user_input)

def print_header():
    header = r"""
  ______              ______                       __                               
 /      \            /      \                     /  |                              
/$$$$$$  | __    __ /$$$$$$  | _______    ______  $$/   ______    ______    _______ 
$$$  \$$ |/  \  /  |$$ |  $$ |/       \  /      \ /  | /      \  /      \  /       |
$$$$  $$ |$$  \/$$/ $$ |  $$ |$$$$$$$  |/$$$$$$  |$$ |/$$$$$$  |/$$$$$$  |/$$$$$$$/ 
$$ $$ $$ | $$  $$<  $$ |  $$ |$$ |  $$ |$$    $$ |$$ |$$ |  $$/ $$ |  $$ |$$      \ 
$$ \$$$$ | /$$$$  \ $$ \__$$ |$$ |  $$ |$$$$$$$$/ $$ |$$ |      $$ \__$$ | $$$$$$  |
$$   $$$/ /$$/ $$  |$$    $$/ $$ |  $$ |$$       |$$ |$$ |      $$    $$/ /     $$/ 
 $$$$$$/  $$/   $$/  $$$$$$/  $$/   $$/  $$$$$$$/ $$/ $$/        $$$$$$/  $$$$$$$/  
"""
    print(Fore.CYAN + header)

def main():
    print_header()
    private_keys = manage_private_keys()

    num_transactions = get_input_with_default("Enter the number of times to repeat the operation", 20, int)
    max_priority_fee = get_input_with_default("Enter max priority fee in Gwei (e.g. 2)", 50, float)
    base_fee_multiplier = get_input_with_default("Enter base fee multiplier (e.g. 1.1 for 10% higher gas)", 1.1, float)
    sleep_time = get_input_with_default("Enter the delay time between batches (in seconds)", 10, int)

    asyncio.run(process_transactions_in_parallel(private_keys, num_transactions, max_priority_fee, base_fee_multiplier, sleep_time))

if __name__ == "__main__":
    main()
